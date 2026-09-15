"""
Wipes all mail data from the db: emails (cascades to attachments) and resets
workflow checkpoint progress back to never_seen. Leaves workflows/runs/logs
rows in place (their email_id/attachment_id just go NULL via ON DELETE SET
NULL) since those aren't "mail", they're history.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mailextractor.models import Email, Checkpoint


def clean_mail(db):
    """Runs the actual wipe against the given session; caller commits/closes."""
    email_count = db.query(Email).delete()
    checkpoint_count = db.query(Checkpoint).update({
        Checkpoint.status: "never_seen",
        Checkpoint.last_seen_at: None,
        Checkpoint.last_successful: None,
        Checkpoint.last_missed: None,
    })
    db.commit()
    return email_count, checkpoint_count


def main():
    from mailextractor.backend.db import SessionLocal
    db = SessionLocal()
    try:
        email_count, checkpoint_count = clean_mail(db)
    finally:
        db.close()

    print(f"Deleted {email_count} email(s) (attachments cascaded).")
    print(f"Reset {checkpoint_count} workflow checkpoint(s) to never_seen.")


if __name__ == "__main__":
    main()
