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

def poll(config):
    """Fetch new mail via the configured provider and insert it, advancing the checkpoint."""
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
    return None

def _run_loop(interval: int) -> None:
    """Polls repeatedly on an interval (mirrors scripts/check_checkpoints.py's
    APScheduler pattern). A failed poll is logged and retried next interval —
    not fatal to the loop — since the skip_hashes mechanism is meant to let an
    operator unwedge it without needing to restart the process."""
    engine = create_engine(config.DATABASE_URL)
    logger = setup_logging(engine)

    def job():
        try:
            poll(config)
        except Exception:
            logger.exception("Scheduled poll failed — will retry next interval", extra={"event_type": "SCHEDULED_POLL_FAILED"})

    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", seconds=interval, next_run_time=datetime.now())

    def shutdown(signum, frame):
        logger.info("Shutting down poll scheduler", extra={"event_type": "POLL_SCHEDULER_SHUTDOWN"})
        scheduler.shutdown(wait=False)

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