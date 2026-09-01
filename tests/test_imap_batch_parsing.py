"""IMAPProvider used to wrap per-item parsing inside the same retry loop as
the network FETCH: a single malformed message deterministically re-failed
every retry, silently dropping the whole batch (good messages included)
after max_retries — with no skip_hashes recovery path, since no content
hash exists for something that never parsed. Uses a mocked IMAP connection
since reproducing a genuine MIME parse failure against a real mailbox isn't
practical or safe.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from mailextractor.app.poller.provider import IMAPProvider


def _make_fetch_response():
    return ("OK", [
        (b"1 (UID 1 RFC822 {10}", b"raw1"), b")",
        (b"2 (UID 2 RFC822 {10}", b"raw2"), b")",
        (b"3 (UID 3 RFC822 {10}", b"raw3"), b")",
    ])


def _fake_parse_raises_on_uid_2(response_line, raw_email):
    if b"UID 2" in response_line:
        raise Exception("malformed message")
    uid = re.search(rb"UID (\d+)", response_line).group(1).decode()
    return {
        "message_id": f"<{uid}@test>", "subject": "s", "sender": "a@b",
        "recipient": "c@d", "date": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "body": "", "html_body": None, "raw_headers": {}, "attachments": [],
        "imap_uid": uid, "email_account": "u",
        "hash": hashlib.sha256(uid.encode()).hexdigest(),
    }


def _provider(monkeypatch, checkpoint_path, fetch_calls):
    def fake_uid(command, *args):
        if command == "search":
            return ("OK", [b"1 2 3"])
        if command == "fetch":
            fetch_calls.append(args)
            return _make_fetch_response()
        raise AssertionError(f"unexpected uid command {command!r}")

    provider = IMAPProvider(
        host="h", port=993, username="u", password="p", use_ssl=True,
        mailbox="INBOX", checkpoint_path=checkpoint_path, max_retries=3,
    )
    monkeypatch.setattr(provider, "_parse_message", _fake_parse_raises_on_uid_2)
    provider._connection = Mock()
    provider._connection.uid.side_effect = fake_uid
    return provider


def test_imap_parse_failure_crashes_without_retrying_the_fetch(monkeypatch):
    fetch_calls = []
    provider = _provider(monkeypatch, checkpoint_path=None, fetch_calls=fetch_calls)

    with pytest.raises(Exception, match="malformed message"):
        list(provider.iterate_mails())

    # not retried — a parse failure is deterministic, retrying re-fetches
    # and re-fails on the exact same message
    assert len(fetch_calls) == 1


def test_imap_parse_failure_can_be_skip_listed_by_uid_hash(monkeypatch, tmp_path):
    uid_2_hash = hashlib.sha256(b"2").hexdigest()
    checkpoint_path = tmp_path / "checkpoint.txt"
    checkpoint_path.write_text(json.dumps({"dt": None, "hash": None, "skip_hashes": [uid_2_hash]}))

    fetch_calls = []
    provider = _provider(monkeypatch, checkpoint_path=str(checkpoint_path), fetch_calls=fetch_calls)

    results = list(provider.iterate_mails())  # must NOT raise

    assert len(fetch_calls) == 1
    assert {r["imap_uid"] for r in results} == {"1", "3"}
