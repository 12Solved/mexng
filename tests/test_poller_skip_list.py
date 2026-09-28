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

