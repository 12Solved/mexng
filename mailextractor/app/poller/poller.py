"""
Polls emails using configured provider (Gmail or IMAP).

Configuration:
    Set EMAIL_PROVIDER in .env to 'gmail' or 'imap'
    Configure provider-specific settings in .env

Usage:
    python poller.py
    python poller.py --filter "UNSEEN"
    python poller.py --from-uid 1 --batch-size 100
    python poller.py --reset
"""
import argparse
import math
import os
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config
from mailextractor.app.poller.providers.gmail_provider import GmailProvider
from mailextractor.app.poller.providers.imap_provider import IMAPProvider
from mailextractor.app.poller.email_inserter import insert_email
from mailextractor.models import MailboxState

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

logger = setup_logging(engine)


def get_provider():
    provider_type = config.EMAIL_PROVIDER.lower()

    if provider_type == "gmail":
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        provider = GmailProvider(
            credentials_path=os.path.join(BASE_DIR, config.GMAIL_CREDENTIALS_PATH.split('/')[-1]),
            token_path=os.path.join(BASE_DIR, config.GMAIL_TOKEN_PATH.split('/')[-1]),
        )
        logger.info("Using Gmail provider", extra={"event_type": "PROVIDER_SELECTED"})

    elif provider_type == "imap":
        if not config.IMAP_USERNAME or not config.IMAP_PASSWORD:
            raise ValueError("IMAP_USERNAME and IMAP_PASSWORD must be set for IMAP provider")

        provider = IMAPProvider(
            host=config.IMAP_HOST,
            port=config.IMAP_PORT,
            username=config.IMAP_USERNAME,
            password=config.IMAP_PASSWORD,
            use_ssl=config.IMAP_USE_SSL,
            mailbox=config.IMAP_MAILBOX,
        )
        logger.info(f"Using IMAP provider ({config.IMAP_HOST})",
                    extra={"event_type": "PROVIDER_SELECTED"})

    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER: {provider_type}. Use 'gmail' or 'imap'")

    return provider


def _get_mailbox_state(session, account: str, mailbox: str) -> MailboxState | None:
    return session.query(MailboxState).filter_by(
        email_account=account, mailbox=mailbox
    ).first()


def _save_mailbox_state(session, account: str, mailbox: str, uidvalidity: str, last_seen_uid: int):
    state = _get_mailbox_state(session, account, mailbox)
    if state is None:
        state = MailboxState(email_account=account, mailbox=mailbox)
        session.add(state)
    state.uidvalidity = uidvalidity
    state.last_seen_uid = str(last_seen_uid)
    session.flush()


def _reset_mailbox_state(session, account: str, mailbox: str):
    state = _get_mailbox_state(session, account, mailbox)
    if state:
        session.delete(state)
        session.flush()
        logger.info(f"Mailbox state reset for {account}/{mailbox}",
                    extra={"event_type": "MAILBOX_STATE_RESET"})
    else:
        logger.info(f"No mailbox state found for {account}/{mailbox}",
                    extra={"event_type": "MAILBOX_STATE_RESET_NOT_FOUND"})


def _insert_batch(session, emails: list[dict]) -> int:
    inserted = 0
    for email_data in emails:
        try:
            result = insert_email(session, email_data)
            session.commit()
            if result:
                inserted += 1
        except Exception:
            session.rollback()
            logger.exception("Failed to insert email, rolled back",
                             extra={"event_type": "EMAIL_INSERT_FAILED"})
    return inserted


def poll(search_filter: str | None = None, batch_size: int = 50, from_uid: int | None = None):
    if config.EMAIL_PROVIDER.lower() != "imap":
        # Gmail path — unchanged behaviour
        provider = get_provider()
        emails = provider.fetch()
        if not emails:
            logger.info("Nothing new.", extra={"event_type": "POLL_NO_RESULTS"})
            return
        session = Session()
        try:
            inserted = _insert_batch(session, emails)
            logger.info(f"Poll complete — {inserted} new email(s) inserted.",
                        extra={"event_type": "POLL_COMPLETE"})
        finally:
            session.close()
        return

    provider = get_provider()
    provider.connect()

    try:
        server_state = provider.fetch_mailbox_state()
        uidvalidity = server_state["uidvalidity"]
        uidnext = int(server_state["uidnext"]) if server_state["uidnext"] else None

        if uidvalidity is None:
            logger.error("Could not retrieve UIDVALIDITY from server - aborting poll",
                 extra={"event_type": "UIDVALIDITY_UNAVAILABLE"})
            return

        session = Session()
        try:
            db_state = _get_mailbox_state(session, provider.username, provider.mailbox)

            # UIDVALIDITY mismatch — halt
            if db_state and db_state.uidvalidity and db_state.uidvalidity != uidvalidity:
                logger.critical(
                    f"UIDVALIDITY changed ({db_state.uidvalidity} -> {uidvalidity}). "
                    "Polling halted. Run with --reset to clear state and resync from scratch.",
                    extra={"event_type": "UIDVALIDITY_CHANGED",
                           "old": db_state.uidvalidity, "new": uidvalidity}
                )
                return

            # Determine starting UID
            if from_uid is not None:
                since_uid = from_uid
            elif db_state and db_state.last_seen_uid:
                since_uid = int(db_state.last_seen_uid) + 1
            else:
                since_uid = 1

            uids = provider.fetch_uids(since_uid, search_filter)

            if not uids:
                logger.info("Nothing new.", extra={"event_type": "POLL_NO_RESULTS"})
                # Advance last_seen_uid to uidnext-1 so next poll doesn't re-scan the full range
                if uidnext and uidnext > 1:
                    _save_mailbox_state(session, provider.username, provider.mailbox,
                                        uidvalidity, uidnext - 1)
                    session.commit()
                return

            # Fetch and insert in batches
            total_batches = math.ceil(len(uids) / batch_size)
            cumulative = 0

            for batch_num in range(1, total_batches + 1):
                batch_uids = uids[(batch_num - 1) * batch_size: batch_num * batch_size]
                emails = provider.fetch_messages(batch_uids, batch_size=batch_size)
                inserted = _insert_batch(session, emails)
                cumulative += inserted
                logger.info(
                    f"Batch {batch_num}/{total_batches}: {len(batch_uids)} UIDs, "
                    f"{len(emails)} fetched, {inserted} inserted",
                    extra={"event_type": "BATCH_COMPLETE", "batch_num": batch_num, "inserted": inserted}
                )

            # Advance last_seen_uid to the highest UID we searched (not just inserted)
            _save_mailbox_state(session, provider.username, provider.mailbox,
                                uidvalidity, max(uids))
            session.commit()

            logger.info(f"Poll complete — {cumulative} new email(s) inserted.",
                        extra={"event_type": "POLL_COMPLETE", "inserted": cumulative})
        finally:
            session.close()
    finally:
        provider.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Email poller")
    parser.add_argument("--filter", type=str, default=None,
                        help='IMAP search filter (e.g., "UNSEEN", \'FROM "user@example.com"\')')
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Emails per fetch batch (default: 50)")
    parser.add_argument("--from-uid", type=int, default=None,
                        help="Start polling from this UID (overrides last_seen_uid; use 1 for full import)")
    parser.add_argument("--reset", action="store_true",
                        help="Clear mailbox state for the configured account and exit")

    args = parser.parse_args()

    if args.reset:
        if config.EMAIL_PROVIDER.lower() != "imap":
            print("--reset only applies to IMAP provider")
            return
        session = Session()
        try:
            _reset_mailbox_state(session, config.IMAP_USERNAME, config.IMAP_MAILBOX)
            session.commit()
        finally:
            session.close()
        return

    poll(
        search_filter=args.filter,
        batch_size=args.batch_size,
        from_uid=args.from_uid,
    )


if __name__ == "__main__":
    main()

