"""Runs one poll: fetch new mail via the configured provider, insert into DB."""
import argparse
import math
import os
import sys
import time

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
        provider.connect()
        for mail in provider.iterate_mails():
            if mail['date'] is None:
                raise ValueError(f"Email missing date (message_id={mail.get('message_id')!r}, subject={mail.get('subject')!r})")
            insert_email(session, mail)
            n_mail = n_mail + 1
            if (max_date is None) or max_date < mail['date']:
                max_date = mail['date']
                max_hash = mail['hash']
        session.commit()
        if max_date:
            provider.update_checkpoint({'dt': max_date, 'hash': max_hash})
        logger.info(f"Poll complete - {n_mail} new email(s) inserted.", extra={"event_type": "POLL_COMPLETE", "inserted": n_mail})
    except Exception as e:
        session.rollback()
        logger.exception("Failed to insert email, rolled back all", extra={"event_type": "EMAIL_INSERT_FAILED", 'error': e})
        raise
    finally:
        provider.disconnect()
        session.close()
    return None

def main():
    poll(config)

if __name__ == "__main__":
    main()