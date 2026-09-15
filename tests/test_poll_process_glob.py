"""Full pipeline test for the glob provider: poll .eml fixtures into the db,
then run them through real workflows, using the db state to check outcomes."""
import glob as globmod
import os

import pytest

from mailextractor.app.poller.poller import poll
from mailextractor.app.processor.processor import process
from mailextractor.models import Email, RunState, WorkflowRun

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "example-data", "emails"
)


def _glob_config(make_config, patterns, **overrides):
    return make_config(EMAIL_PROVIDER="glob", GLOB_PATTERNS=",".join(patterns), **overrides)


def test_glob_poll_then_process_full_pipeline(make_config, load_workflows, db_session, tmp_path):
    # no_date_header.eml is a deliberate "missing date" fixture (see
    # test_glob_poll_rolls_back_on_missing_date below) — exclude it here so
    # this test covers the happy path.
    fixtures = sorted(
        f for f in globmod.glob(os.path.join(FIXTURES_DIR, "*.eml"))
        if os.path.basename(f) != "no_date_header.eml"
    )
    assert fixtures, "expected .eml fixtures under example-data/emails"

    invoice_wf, filter_wf = load_workflows(
        "date_step_invoice.json",
        "sender_recipient_filter.json",
        patch_destination=str(tmp_path / "attachments"),
    )

    config = _glob_config(make_config, fixtures)

    poll(config)

    emails = db_session.query(Email).all()
    assert len(emails) == len(fixtures)

    process(config)

    # date_step_invoice.json has no sender/recipient filtering and targets
    # invoice_report.eml — should succeed and save an attachment.
    invoice_email = db_session.query(Email).filter(Email.message_id.like("%invoice4471%")).one()
    invoice_run = db_session.query(WorkflowRun).filter_by(email_id=invoice_email.id, workflow_id=invoice_wf.id).one()
    assert invoice_run.state == RunState.success
    saved = list((tmp_path / "attachments").rglob("invoice-due-*"))
    assert saved, "expected date_step_invoice to save an attachment under tmp_path"

    # sender_recipient_filter.json: sender_recipient_match_to.eml matches both
    # the sender and recipient patterns -> success (and an attachment saved).
    match_email = db_session.query(Email).filter(Email.message_id.like("%senderrecipto0001%")).one()
    match_run = db_session.query(WorkflowRun).filter_by(email_id=match_email.id, workflow_id=filter_wf.id).one()
    assert match_run.state == RunState.success

    # sender_recipient_nomatch.eml: sender matches but no recipient header
    # does -> match_recipient_address_step stops the branch -> skipped.
    nomatch_email = db_session.query(Email).filter(Email.message_id.like("%senderrecptno0001%")).one()
    nomatch_run = db_session.query(WorkflowRun).filter_by(email_id=nomatch_email.id, workflow_id=filter_wf.id).one()
    assert nomatch_run.state == RunState.skipped

    # re-polling is idempotent: the checkpoint should stop everything from
    # being re-fetched/re-inserted.
    poll(config)
    assert db_session.query(Email).count() == len(fixtures)


def test_glob_poll_rolls_back_on_missing_date(make_config, db_session):
    fixtures = [
        os.path.join(FIXTURES_DIR, "no_date_header.eml"),
        os.path.join(FIXTURES_DIR, "invoice_report.eml"),
    ]
    config = _glob_config(make_config, fixtures)

    with pytest.raises(ValueError, match="missing date"):
        poll(config)

    # the whole batch (including the otherwise-valid invoice email that sorts
    # before the bad one) must be rolled back, not partially inserted.
    assert db_session.query(Email).count() == 0
