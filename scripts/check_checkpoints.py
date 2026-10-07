"""
Checks all checkpoints against their interval schedule, updates statuses, and
advances next_expected_at when a deadline window closes.

This is the sole authority for schedule progression. TimeoutStep only stamps
last_seen_at when an email arrives; this checker decides whether that arrival
was on time or late and rolls the schedule forward.

Per-checkpoint logic (runs when now > next_expected_at):
  - Window is (window_start_at, next_expected_at]; window_start_at is set to
    now on each evaluation (fallback: one normal interval before the deadline).
  - If last_seen_at falls within the window:
      status = "ok", next_expected_at snapped to next grid slot from reference_timestamp
  - Otherwise (no touch in the window):
      status = "missed", next_expected_at advanced by late_interval_hours (or
      normal if unset) to the first deadline after now

Status values:
  never_seen  — checkpoint has never been touched (last_seen_at is None)
  ok          — last arrival was within the expected window
  missed      — deadline passed without a touch

Usage:
    python check_checkpoints.py
"""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mailextractor import models
from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config


logger = logging.getLogger(__name__)


def _next_scheduled_slot(reference: datetime, interval_hours: int, after: datetime) -> datetime:
    """Return the next tick on the reference grid that is strictly after `after`."""
    interval = timedelta(hours=interval_hours)
    elapsed = after - reference
    periods = int(elapsed / interval)  # floor
    candidate = reference + periods * interval
    if candidate <= after:
        candidate += interval
    return candidate


def check_once(config=config, engine=None):
    owns_engine = engine is None
    if owns_engine:
        engine = create_engine(config.DATABASE_URL)
    session = sessionmaker(bind=engine)()
    try:
        checkpoints = session.query(models.Checkpoint).all()
        if not checkpoints:
            return

        updated = 0
        missed = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for cp in checkpoints:
            # Start where the last evaluation left off so an arrival counts once.
            window_start = cp.window_start_at or (
                cp.next_expected_at - timedelta(hours=cp.normal_interval_hours)
            )
            if cp.last_seen_at is None:
                new_status = "never_seen"
            elif now > cp.next_expected_at:
                # Deadline has passed — evaluate whether the window was hit.
                if cp.last_seen_at > window_start:
                    # Email arrived within the window — snap back to original grid.
                    new_status = "ok"
                    cp.last_successful = cp.last_seen_at
                    cp.next_expected_at = _next_scheduled_slot(
                        cp.reference_timestamp, cp.normal_interval_hours, now
                    )
                else:
                    # No touch in the window. Jump past now so downtime gives one miss.
                    new_status = "missed"
                    missed.append((cp.name, cp.next_expected_at))
                    cp.last_missed = now
                    interval = cp.late_interval_hours if cp.late_interval_hours else cp.normal_interval_hours
                    cp.next_expected_at = _next_scheduled_slot(cp.next_expected_at, interval, now)
                cp.window_start_at = now
            elif cp.status == "missed" and cp.last_seen_at <= window_start:
                # Window still open but nothing has arrived since the miss.
                new_status = "missed"
            else:
                # Window still open.
                new_status = "ok"

            if cp.status != new_status:
                cp.status = new_status
                updated += 1

        session.commit()

        # Logged on every missed window, not only on the ok -> missed
        # transition, so a feed that stays down keeps alerting each window.
        for name, deadline in sorted(missed):
            logger.warning(
                f"Checkpoint '{name}' missed deadline {deadline}",
                extra={"event_type": "CHECKPOINT_MISSED"},
            )

        if updated:
            logger.info(
                f"Checkpoint check complete - {updated} status(es) updated",
                extra={"event_type": "CHECKPOINT_CHECK_COMPLETE"},
            )
    except Exception:
        session.rollback()
        logger.exception("Checkpoint check failed", extra={"event_type": "CHECKPOINT_CHECK_FAILED"})
    finally:
        session.close()
        if owns_engine:
            engine.dispose()


if __name__ == "__main__":
    setup_logging(create_engine(config.DATABASE_URL))
    check_once()
