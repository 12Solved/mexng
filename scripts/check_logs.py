"""
Scans the `logs` table for new rows, matches them against enabled
`alert_rules` and queues each match in `alert_queue` (one row per user per
log, however many of that user's rules match).

Progress is tracked by the single-row `alert_scan_state` cursor (id of the
last log row scanned), so a restart doesn't replay the whole history.

Runs as a standalone process with APScheduler.

Usage:
    python check_logs.py
    python check_logs.py --interval 300
"""
import argparse
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from itertools import takewhile

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import and_, create_engine, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mailextractor import models
from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config

# Log ids are assigned at insert but become visible at commit, so a row
# younger than this may still have an uncommitted lower-id sibling.
SAFETY_MARGIN_SECONDS = 10

# The checker's own events are never queued, so a failing scan can't
# alert about itself in a loop.
SELF_EVENT_PREFIX = "CHECK_LOGS_"

logger = logging.getLogger(__name__)

logging.getLogger("apscheduler").propagate = False


def _queue_matches(session, after_id: int, up_to_id: int) -> int:
    Log, AlertRule = models.Log, models.AlertRule
    matches = (
        select(AlertRule.user_id, Log.id)
        .join(
            AlertRule,
            and_(
                AlertRule.enabled.is_(True),
                or_(AlertRule.event_type.is_(None), AlertRule.event_type == Log.event_type),
                or_(AlertRule.workflow_id.is_(None), AlertRule.workflow_id == Log.workflow_id),
                or_(AlertRule.checkpoint_id.is_(None), AlertRule.checkpoint_id == Log.checkpoint_id),
                # log_level is a Postgres enum, ordered DEBUG < ... < CRITICAL.
                Log.level >= AlertRule.min_level,
            ),
        )
        .where(
            Log.id > after_id,
            Log.id <= up_to_id,
            ~Log.event_type.startswith(SELF_EVENT_PREFIX, autoescape=True),
        )
        .distinct()
    )
    result = session.execute(
        pg_insert(models.AlertQueue)
        .from_select(["user_id", "log_id"], matches)
        .on_conflict_do_nothing(constraint="alert_queue_user_log_key")
    )
    return result.rowcount


def check_once(config=config, engine=None, safety_margin_seconds: int = SAFETY_MARGIN_SECONDS):
    owns_engine = engine is None
    if owns_engine:
        engine = create_engine(config.DATABASE_URL)
    session = sessionmaker(bind=engine)()
    try:
        state = session.get(models.AlertScanState, 1)
        # DB clock, matching how logs.created_at is stamped.
        cutoff = session.scalar(select(func.localtimestamp() - timedelta(seconds=safety_margin_seconds)))

        new_rows = (
            session.query(models.Log)
            .filter(models.Log.id > state.last_log_id)
            .order_by(models.Log.id.asc())
            .all()
        )
        # Stop at the first row inside the margin rather than skipping it, so
        # the cursor can't move past a lower id that hasn't committed yet.
        scanned = list(takewhile(lambda row: row.created_at < cutoff, new_rows))

        queued = 0
        if scanned:
            queued = _queue_matches(session, state.last_log_id, scanned[-1].id)
            state.last_log_id = scanned[-1].id
        session.commit()

        logger.info(
            f"Log scan complete - {len(scanned)} row(s) scanned, {queued} queued",
            extra={"event_type": "CHECK_LOGS_COMPLETE"},
        )
    except Exception:
        session.rollback()
        logger.error("Log check failed", extra={"event_type": "CHECK_LOGS_FAILED"})
    finally:
        session.close()
        if owns_engine:
            engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=300, help="Seconds between checks (default: 300)")
    args = parser.parse_args()

    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    setup_logging(engine)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        check_once,
        "interval",
        seconds=args.interval,
        next_run_time=datetime.now(),
        kwargs={"engine": engine},
    )

    def shutdown(signum, frame):
        logger.info("Shutting down log scheduler", extra={"event_type": "CHECK_LOGS_SCHEDULER_SHUTDOWN"})
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info(
        f"Log scheduler started (interval: {args.interval}s)",
        extra={"event_type": "CHECK_LOGS_SCHEDULER_STARTED"},
    )
    scheduler.start()


if __name__ == "__main__":
    main()
