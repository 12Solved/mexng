"""
Polls the `logs` table for new ERROR/CRITICAL rows matching a curated
event_type allowlist and sends a batched digest via notify().

Progress is tracked with a local watermark file (id of the last log row
scanned) so a restart doesn't replay the whole history, and so a quiet tick
doesn't keep rescanning an ever-growing range of already-seen rows.

Runs as a standalone process with APScheduler.

Usage:
    python check_logs.py
    python check_logs.py --interval 300 --state-file /path/to/state.json
"""
import argparse
import json
import logging
import os
import signal
import sys
import tempfile
from collections import defaultdict
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mailextractor import models
from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config
from notify import notify

DEFAULT_STATE_FILE = os.path.join(os.path.dirname(__file__), "check_logs_state.json")
ALERT_EVENT_TYPES = {"PATH_JAIL_VIOLATION", "WORKFLOW_FAILED", "ARCHIVE_EXTRACT_FAILED", "CHECKPOINT_CHECK_FAILED"}
ALERT_LEVELS = {models.LogLevel.ERROR, models.LogLevel.CRITICAL}

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

logger = setup_logging(engine)

logging.getLogger("apscheduler").propagate = False


def _read_watermark(state_file: str, session) -> int:
    try:
        with open(state_file, "r") as f:
            return json.load(f)["last_log_id"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return session.query(func.max(models.Log.id)).scalar() or 0


def _write_watermark(state_file: str, last_log_id: int) -> None:
    dir_ = os.path.dirname(state_file) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix=".check_logs_state_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"last_log_id": last_log_id}, f)
        os.replace(tmp_path, state_file)
    except Exception:
        os.remove(tmp_path)
        raise


def _build_digest(rows) -> str:
    by_type = defaultdict(list)
    for row in rows:
        by_type[row.event_type].append(row)

    lines = []
    for event_type, entries in sorted(by_type.items()):
        latest = max(entries, key=lambda r: r.id)
        lines.append(
            f"- {event_type}: {len(entries)} occurrence(s), latest at {latest.created_at} - {latest.message}"
        )
    return "\n".join(lines)


def check_once(state_file: str):
    session = Session()
    try:
        last_log_id = _read_watermark(state_file, session)

        new_rows = (
            session.query(models.Log)
            .filter(models.Log.id > last_log_id)
            .order_by(models.Log.id.asc())
            .all()
        )

        alert_rows = [
            row for row in new_rows
            if row.level in ALERT_LEVELS and row.event_type in ALERT_EVENT_TYPES
        ]

        if alert_rows:
            notify(
                subject=f"{len(alert_rows)} alert-worthy log(s) detected",
                body=_build_digest(alert_rows),
                meta={"count": len(alert_rows)},
            )

        if new_rows:
            _write_watermark(state_file, max(row.id for row in new_rows))
        elif not os.path.exists(state_file):
            # First run against an empty/all-historical table
            _write_watermark(state_file, last_log_id)

        logger.info(
            f"Log check complete - {len(new_rows)} row(s) scanned, {len(alert_rows)} alert-worthy",
            extra={"event_type": "CHECK_LOGS_COMPLETE"},
        )
    except Exception:
        session.rollback()
        logger.error("Log check failed", extra={"event_type": "CHECK_LOGS_FAILED"})
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=300, help="Seconds between checks (default: 300)")
    parser.add_argument("--state-file", type=str, default=DEFAULT_STATE_FILE, help="Path to watermark state file")
    args = parser.parse_args()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        check_once,
        "interval",
        seconds=args.interval,
        next_run_time=datetime.now(),
        kwargs={"state_file": args.state_file},
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
