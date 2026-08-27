"""
Checks all checkpoints against their interval schedule, updates statuses, and
advances next_expected_at when a deadline window closes.

This is the sole authority for schedule progression. TimeoutStep only stamps
last_seen_at when an email arrives; this checker decides whether that arrival
was on time or late and rolls the schedule forward.

Per-checkpoint logic (runs when now > next_expected_at):
  - If last_seen_at falls within the closed window (window_start, next_expected_at]:
      status = "ok", next_expected_at snapped to next grid slot from reference_timestamp
  - Otherwise (no touch in the window):
      status = "missed", next_expected_at += late_interval_hours (or normal if unset)

When now <= next_expected_at the window is still open; status reflects whether
an arrival has been recorded in this window but next_expected_at is not changed.

Status values:
  never_seen  — checkpoint has never been touched (last_seen_at is None)
  ok          — last arrival was within the expected window
  missed      — deadline passed without a touch

Runs as a standalone process with APScheduler.

Usage:
    python check_checkpoints.py
    python check_checkpoints.py --interval 300
"""
import argparse
import logging
import os
import signal
import sys
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mailextractor import models
from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config
from notify import notify


engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

logger = setup_logging(engine)

logging.getLogger("apscheduler").propagate = False


def _next_scheduled_slot(reference: datetime, interval_hours: int, after: datetime) -> datetime:
    """Return the next tick on the reference grid that is strictly after `after`."""
    interval = timedelta(hours=interval_hours)
    elapsed = after - reference
    periods = int(elapsed / interval)  # floor
    candidate = reference + periods * interval
    if candidate <= after:
        candidate += interval
    return candidate


def check_once():
    session = Session()
    try:
        checkpoints = session.query(models.Checkpoint).all()
        if not checkpoints:
            return

        updated = 0
        newly_missed = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for cp in checkpoints:
            if cp.last_seen_at is None:
                new_status = "never_seen"
            elif now > cp.next_expected_at:
                # Deadline has passed — evaluate whether the window was hit.
                window_start = cp.next_expected_at - timedelta(hours=cp.normal_interval_hours)
                if cp.last_seen_at > window_start:
                    # Email arrived within the window — snap back to original grid.
                    new_status = "ok"
                    cp.last_successful = cp.last_seen_at
                    cp.next_expected_at = _next_scheduled_slot(
                        cp.reference_timestamp, cp.normal_interval_hours, now
                    )
                else:
                    # No touch in the window.
                    new_status = "missed"
                    cp.last_missed = now
                    interval = cp.late_interval_hours if cp.late_interval_hours else cp.normal_interval_hours
                    cp.next_expected_at = cp.next_expected_at + timedelta(hours=interval)
            else:
                # Window still open.
                new_status = "ok" if cp.last_seen_at is not None else "never_seen"

            if cp.status != new_status:
                if new_status == "missed":
                    newly_missed.append((cp.name, cp.next_expected_at))
                cp.status = new_status
                updated += 1

        session.commit()

        if newly_missed:
            body = "\n".join(
                f"- {name}: deadline passed at {deadline}"
                for name, deadline in sorted(newly_missed)
            )
            notify(
                subject=f"{len(newly_missed)} checkpoint(s) missed",
                body=body,
                recipients="",
                meta={"count": len(newly_missed)},
            )

        logger.info(
            f"Checkpoint check complete - {updated} status(es) updated",
            extra={"event_type": "CHECKPOINT_CHECK_COMPLETE"},
        )
    except Exception:
        session.rollback()
        logger.error("Checkpoint check failed", extra={"event_type": "CHECKPOINT_CHECK_FAILED"})
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=300, help="Seconds between checks (default: 300)")
    args = parser.parse_args()

    scheduler = BlockingScheduler()
    scheduler.add_job(check_once, "interval", seconds=args.interval, next_run_time=datetime.now())

    def shutdown(signum, frame):
        logger.info("Shutting down checkpoint scheduler", extra={"event_type": "CHECKPOINT_SCHEDULER_SHUTDOWN"})
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info(
        f"Checkpoint scheduler started (interval: {args.interval}s)",
        extra={"event_type": "CHECKPOINT_SCHEDULER_STARTED"},
    )
    scheduler.start()


if __name__ == "__main__":
    main()
