"""
Wipes all mail data from the db: emails (cascades to attachments), mailbox
poll state, and resets workflow checkpoint progress back to never_seen.
Leaves workflows/runs/logs rows in place (their email_id/attachment_id just
go NULL via ON DELETE SET NULL) since those aren't "mail", they're history.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mailextractor.backend.db import SessionLocal
from mailextractor.models import Email, MailboxState, Checkpoint


def main():
    db = SessionLocal()
    try:
        email_count = db.query(Email).delete()
        mailbox_state_count = db.query(MailboxState).delete()
        checkpoint_count = db.query(Checkpoint).update({
            Checkpoint.status: "never_seen",
            Checkpoint.last_seen_at: None,
            Checkpoint.last_successful: None,
            Checkpoint.last_missed: None,
        })
        db.commit()
    finally:
        db.close()

    print(f"Deleted {email_count} email(s) (attachments cascaded).")
    print(f"Cleared {mailbox_state_count} mailbox poll state row(s).")
    print(f"Reset {checkpoint_count} workflow checkpoint(s) to never_seen.")


if __name__ == "__main__":
    main()
