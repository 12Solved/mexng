"""scripts/make/clean_mail.py imported the deleted
MailboxState model, so `make clean-mail` raised ImportError before doing
anything. The import above would already fail collection if that regressed."""
from datetime import datetime, timedelta

from scripts.make.clean_mail import clean_mail
from mailextractor.models import Checkpoint, Email


def test_clean_mail_deletes_emails_and_resets_checkpoints(db_session):
    db_session.add(Email(message_id="<a@b>", subject="s", sender="x@y", recipient="y@x", date=datetime.now()))
    db_session.add(Checkpoint(
        name="test-checkpoint",
        reference_timestamp=datetime.now(),
        normal_interval_hours=24,
        next_expected_at=datetime.now() + timedelta(hours=24),
        status="ok",
        last_seen_at=datetime.now(),
    ))
    db_session.commit()

    email_count, checkpoint_count = clean_mail(db_session)

    assert email_count == 1
    assert checkpoint_count == 1
    assert db_session.query(Email).count() == 0
    cp = db_session.query(Checkpoint).one()
    assert cp.status == "never_seen"
    assert cp.last_seen_at is None
