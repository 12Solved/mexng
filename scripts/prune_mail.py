"""
Deletes emails (attachments cascade) created before a given date.
Checkpoints are left alone, so pruned mail isn't re-fetched.

Usage: python scripts/prune_mail.py --before 2026-01-01 [--dry-run] [-y]
"""
import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mailextractor.models import Email


def prune_mail(db, cutoff):
    """Deletes mail created before `cutoff` and commits; returns the email count."""
    count = db.query(Email).filter(Email.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Delete mail created before a date.")
    parser.add_argument("--before", type=datetime.fromisoformat, required=True, help="e.g. 2026-01-01")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    args = parser.parse_args(argv)

    from mailextractor.backend.db import SessionLocal
    db = SessionLocal()
    try:
        count = db.query(Email).filter(Email.created_at < args.before).count()
        print(f"Delete {count} email(s) created before {args.before:%Y-%m-%d %H:%M:%S}.")
        if args.dry_run or count == 0:
            return
        if not args.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("Aborted.")
        prune_mail(db, args.before)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
