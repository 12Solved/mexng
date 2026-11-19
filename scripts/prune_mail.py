"""
Deletes emails (attachments cascade) created before a given date,
plus alert_queue rows queued before it (sent or not).
Checkpoints are left alone, so pruned mail isn't re-fetched.

Usage: python scripts/prune_mail.py --before 2026-01-01 [--dry-run] [-y]
"""
import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mailextractor.models import AlertQueue, Email


def prune_mail(db, cutoff):
    """Deletes mail and alert queue rows before `cutoff` and commits; returns (email_count, alert_count)."""
    email_count = db.query(Email).filter(Email.created_at < cutoff).delete(synchronize_session=False)
    alert_count = db.query(AlertQueue).filter(AlertQueue.queued_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return email_count, alert_count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Delete mail and alert queue rows before a date.")
    parser.add_argument("--before", type=datetime.fromisoformat, required=True, help="e.g. 2026-01-01")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    args = parser.parse_args(argv)

    from mailextractor.backend.db import SessionLocal
    db = SessionLocal()
    try:
        email_count = db.query(Email).filter(Email.created_at < args.before).count()
        alert_count = db.query(AlertQueue).filter(AlertQueue.queued_at < args.before).count()
        print(f"Delete {email_count} email(s) created and {alert_count} alert queue row(s) "
              f"queued before {args.before:%Y-%m-%d %H:%M:%S}.")
        if args.dry_run or (email_count == 0 and alert_count == 0):
            return
        if not args.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("Aborted.")
        prune_mail(db, args.before)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
