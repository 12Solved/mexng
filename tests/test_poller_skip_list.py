"""Tests for the manual skip_hashes mechanism:
an operator can add a hash to checkpoint.txt's skip_hashes to unwedge a
poller stuck on a poison-pill email, without the poller silently swallowing
*unknown* poison pills (those must still crash loud)."""
import hashlib
import json
import os

import pytest

from mailextractor.app.poller.poller import poll
from mailextractor.app.poller.provider import GLOBProvider
from mailextractor.models import Email

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "example-data", "emails"
)


def _glob_config(make_config, patterns, checkpoint_path):
    return make_config(EMAIL_PROVIDER="glob", GLOB_PATTERNS=",".join(patterns), CHECKPOINT_PATH=checkpoint_path)


def _write_checkpoint(path, skip_hashes):
    with open(path, "w") as f:
        json.dump({"dt": None, "hash": None, "skip_hashes": skip_hashes}, f)


def test_skip_listed_email_hash_is_skipped_not_raised(make_config, db_session, tmp_path):
    no_date_path = os.path.join(FIXTURES_DIR, "no_date_header.eml")
    invoice_path = os.path.join(FIXTURES_DIR, "invoice_report.eml")

    # Compute the real content-hash the same way the provider does, rather
    # than hardcoding it, so this doesn't rot if the fixture changes.
    bad_hash = GLOBProvider([], checkpoint_path=str(tmp_path / "unused"))._parse_message(no_date_path)["hash"]

    checkpoint_path = tmp_path / "checkpoint.txt"
    _write_checkpoint(checkpoint_path, skip_hashes=[bad_hash])

    config = _glob_config(make_config, [no_date_path, invoice_path], str(checkpoint_path))

    poll(config)  # must NOT raise now that the poison pill is skip-listed

    emails = db_session.query(Email).all()
    assert len(emails) == 1
    assert "invoice4471" in emails[0].message_id

    # skip_hashes must survive update_checkpoint()'s rewrite untouched.
    with open(checkpoint_path) as f:
        data = json.load(f)
    assert data["skip_hashes"] == [bad_hash]


def test_unknown_poison_pill_still_crashes_and_rolls_back(make_config, db_session, tmp_path):
    """Same fixtures as above, but nothing skip-listed — must behave exactly
    like the no-skip-list rollback test (crash loud on unrecognized bad mail)."""
    no_date_path = os.path.join(FIXTURES_DIR, "no_date_header.eml")
    invoice_path = os.path.join(FIXTURES_DIR, "invoice_report.eml")

    checkpoint_path = tmp_path / "checkpoint.txt"
    _write_checkpoint(checkpoint_path, skip_hashes=[])

    config = _glob_config(make_config, [no_date_path, invoice_path], str(checkpoint_path))

    with pytest.raises(ValueError, match="missing date"):
        poll(config)

    assert db_session.query(Email).count() == 0


def test_glob_file_parse_failure_can_be_skip_listed_by_path_hash(make_config, db_session, tmp_path):
    missing_file = str(tmp_path / "does-not-exist.eml")
    invoice_path = os.path.join(FIXTURES_DIR, "invoice_report.eml")
    path_hash = hashlib.sha256(missing_file.encode()).hexdigest()

    checkpoint_path = tmp_path / "checkpoint.txt"

    # Not skip-listed yet: the file-parse failure must still crash and roll
    # back the whole batch, including the otherwise-valid invoice email.
    _write_checkpoint(checkpoint_path, skip_hashes=[])
    config = _glob_config(make_config, [missing_file, invoice_path], str(checkpoint_path))
    with pytest.raises(Exception, match="File not found"):
        poll(config)
    assert db_session.query(Email).count() == 0

    # Skip-list it by its path hash (the only hash available pre-parse) ->
    # the rest of the batch now goes through.
    _write_checkpoint(checkpoint_path, skip_hashes=[path_hash])
    poll(config)
    emails = db_session.query(Email).all()
    assert len(emails) == 1
    assert "invoice4471" in emails[0].message_id
