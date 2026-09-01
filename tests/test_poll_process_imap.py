"""Full pipeline test for the IMAP provider, against the real mailbox
configured in .env (IMAP_USERNAME/IMAP_PASSWORD). Skipped automatically if
those aren't set, e.g. in an environment without real credentials.

Content of the real inbox isn't controlled by this test, so assertions stay
generic (pipeline completes, every fetched email gets exactly one terminal
run, re-polling doesn't duplicate) rather than asserting on specific emails.
The checkpoint is seeded to "7 days ago" to keep each run bounded and fast.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from mailextractor.app.poller.poller import poll
from mailextractor.app.processor.processor import process
from mailextractor.models import Email, RunState, WorkflowRun

pytestmark = pytest.mark.skipif(
    not (os.environ.get("IMAP_USERNAME") and os.environ.get("IMAP_PASSWORD")),
    reason="IMAP_USERNAME/IMAP_PASSWORD not set — this test hits a real mailbox",
)


def test_imap_poll_then_process_full_pipeline(make_config, insert_workflow, db_session, tmp_path):
    checkpoint_path = tmp_path / "imap_checkpoint.txt"
    checkpoint_path.write_text(json.dumps({
        "dt": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
        "hash": None,
    }))

    # No sender/recipient/subject filtering — this just needs to apply
    # uniformly to whatever real mail shows up.
    probe_workflow = insert_workflow({
        "name": "imap probe (extract attachments only, no filtering)",
        "steps": [{"type": "extract_attachment_step"}],
    })

    config = make_config(
        EMAIL_PROVIDER="imap",
        IMAP_HOST=os.environ.get("IMAP_HOST", "imap.gmail.com"),
        IMAP_PORT=int(os.environ.get("IMAP_PORT", "993")),
        IMAP_USERNAME=os.environ["IMAP_USERNAME"],
        IMAP_PASSWORD=os.environ["IMAP_PASSWORD"],
        IMAP_USE_SSL=os.environ.get("IMAP_USE_SSL", "true").lower() == "true",
        IMAP_MAILBOX=os.environ.get("IMAP_MAILBOX", "INBOX"),
        CHECKPOINT_PATH=str(checkpoint_path),
    )

    poll(config)  # real network call — must connect, fetch, and not raise

    emails = db_session.query(Email).all()

    process(config)  # must complete even if emails is empty

    for email in emails:
        runs = db_session.query(WorkflowRun).filter_by(email_id=email.id, workflow_id=probe_workflow.id).all()
        assert len(runs) == 1
        assert runs[0].state in (RunState.success, RunState.skipped, RunState.failed)

    # re-polling is idempotent: same checkpoint window shouldn't duplicate
    # whatever was just fetched.
    poll(config)
    assert db_session.query(Email).count() == len(emails)
