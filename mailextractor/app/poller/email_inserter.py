"""Inserts a parsed mail dict (from any provider) as an Email + Attachment rows."""
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from mailextractor.models import Email, Attachment

logger = logging.getLogger(__name__)


def insert_email(session, email_data: dict) -> Email | None:
    """Insert an email and its attachments. Does not commit — caller manages the transaction."""
    message_id = email_data.get("message_id")

    email = Email(
        message_id=message_id,
        subject=email_data.get("subject"),
        sender=email_data.get("sender"),
        recipient=email_data.get("recipient"),
        date=email_data.get("date"),
        body=email_data.get("body"),
        html_body=email_data.get("html_body"),
        raw_headers=email_data.get("raw_headers"),
    )
    session.add(email)
    session.flush()

    for att in email_data.get("attachments", []):
        session.add(Attachment(
            email_id=email.id,
            filename=att["filename"],
            content_type=att.get("content_type"),
            size=att.get("size"),
            content=att.get("content"),
        ))

    logger.info(f"Inserted email: {email.subject!r} (message_id: {message_id})",
                extra={"event_type": "EMAIL_INSERTED", "message_id": message_id})
    return email

