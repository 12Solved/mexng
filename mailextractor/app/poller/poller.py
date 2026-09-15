"""Runs one poll: fetch new mail via the configured provider, insert into DB."""
import argparse
import os
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from mailextractor.app.poller.provider import get_provider
from mailextractor.app.config import config
from mailextractor.app.poller.email_inserter import insert_email
from mailextractor.app.app_logging.setup_logging import setup_logging

def poll(config, engine=None):
    """Fetch new mail via the configured provider and insert it, advancing the checkpoint.
    If no engine is given, creates and disposes its own (fine for one-shot
    use, and required for tests to stay isolated to their own config's db —
    see _run_loop, which passes in one long-lived engine reused across ticks
    instead of leaking a fresh pool every interval)."""
    owns_engine = engine is None
    if owns_engine:
        engine = create_engine(config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    logger = setup_logging(engine)
    provider = get_provider(config = config, logger = logger, checkpoint_path = config.CHECKPOINT_PATH)
    session = Session()
    try:
        n_mail = 0
        max_date = None
        max_hash = None
        mail = None
        provider.connect()
        for mail in provider.iterate_mails():
            if mail['date'] is None:
                logger.error(
                    "Email missing date",
                    extra={"event_type": "POISON_PILL_EMAIL", "hash": mail.get('hash'), "message_id": mail.get('message_id')},
                )
                raise ValueError(f"Email missing date (hash={mail.get('hash')!r}, message_id={mail.get('message_id')!r})")
            insert_email(session, mail)
            n_mail = n_mail + 1
            # dedup key = single latest-dated hash; two emails sharing that exact
            # second would let the older slip through again (assumed rare/ok)
            if (max_date is None) or max_date < mail['date']:
                max_date = mail['date']
                max_hash = mail['hash']
        session.commit()
        if max_date:
            provider.update_checkpoint({'dt': max_date, 'hash': max_hash})
        logger.info(f"Poll complete - {n_mail} new email(s) inserted.", extra={"event_type": "POLL_COMPLETE", "inserted": n_mail})
    except Exception as e:
        session.rollback()
        logger.exception(
            "Failed to insert email, rolled back all",
            extra={
                "event_type": "EMAIL_INSERT_FAILED",
                'error': e,
                'hash': mail.get('hash') if mail else None,
                'message_id': mail.get('message_id') if mail else None,
            },
        )
        raise
    finally:
        provider.disconnect()
        session.close()
        if owns_engine:
            engine.dispose()
    return None

CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD = 3

class LoopFailureTracker:
    """Tracks consecutive poll() failures across scheduled ticks and escalates
    the log level once they cross CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD.
    A single failure could be a one-off poison pill (fine to just retry next
    interval); failing on every consecutive interval instead suggests
    something that won't self-heal (expired IMAP credentials, a dead DB) —
    escalating to CRITICAL makes that visible to log-based monitoring,
    distinct from the routine-failure case. Resets to 0 on any success."""
    def __init__(self, logger):
        self._logger = logger
        self.consecutive_failures = 0

    def run(self, poll_fn):
        try:
            poll_fn()
            self.consecutive_failures = 0
        except Exception:
            self.consecutive_failures += 1
            if self.consecutive_failures >= CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD:
                self._logger.critical(
                    f"Scheduled poll has failed {self.consecutive_failures} times in a row — needs operator attention",
                    exc_info=True,
                    extra={"event_type": "SCHEDULED_POLL_FAILING_REPEATEDLY", "consecutive_failures": self.consecutive_failures},
                )
            else:
                self._logger.exception(
                    "Scheduled poll failed — will retry next interval",
                    extra={"event_type": "SCHEDULED_POLL_FAILED", "consecutive_failures": self.consecutive_failures},
                )

def _run_loop(interval: int) -> None:
    """Polls repeatedly on an interval (mirrors scripts/check_checkpoints.py's
    APScheduler pattern). One engine is created here and reused for every
    tick's poll() call — poll() itself creates+disposes a fresh one per call
    by default (needed so tests stay isolated to their own config's db), but
    that would leak a pool every interval in a long-lived --loop process."""
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    logger = setup_logging(engine)
    tracker = LoopFailureTracker(logger)

    def job():
        tracker.run(lambda: poll(config, engine=engine))

    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", seconds=interval, next_run_time=datetime.now())

    def shutdown(signum, frame):
        logger.info("Shutting down poll scheduler", extra={"event_type": "POLL_SCHEDULER_SHUTDOWN"})
        scheduler.shutdown(wait=False)
        engine.dispose()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info(f"Poll scheduler started (interval: {interval}s)", extra={"event_type": "POLL_SCHEDULER_STARTED"})
    scheduler.start()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Poll repeatedly on an interval instead of once")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between polls when --loop is set (default: 300)")
    args = parser.parse_args()

    if args.loop:
        _run_loop(args.interval)
    else:
        poll(config)

if __name__ == "__main__":
    main()