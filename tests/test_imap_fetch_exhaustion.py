"""A FETCH batch that exhausted all retries used to just log a WARNING and
move to the next batch — but if a later batch succeeds with newer dates, the
checkpoint advances past the dropped batch, permanently excluding it from
every future SINCE search (no skip_hashes recovery, since nothing was ever
fetched to hash). Must crash instead, matching the parse-failure behavior,
so the checkpoint never advances past a run with a failed batch.
"""
import hashlib
import re
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from mailextractor.app.poller.provider import IMAPProvider


def _fake_parse(response_line, raw_email):
    uid = re.search(rb"UID (\d+)", response_line).group(1).decode()
    return {
        "message_id": f"<{uid}@test>", "subject": "s", "sender": "a@b",
        "recipient": "c@d", "date": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "body": "", "html_body": None, "raw_headers": {}, "attachments": [],
        "imap_uid": uid, "email_account": "u",
        "hash": hashlib.sha256(uid.encode()).hexdigest(),
    }


def test_fetch_exhaustion_on_a_later_batch_crashes_without_losing_earlier_yields(monkeypatch):
    monkeypatch.setattr("mailextractor.app.poller.provider.time.sleep", lambda _: None)

    def fake_uid(command, *args):
        if command == "search":
            return ("OK", [b"1 2"])  # two UIDs -> two batches of size 1
        if command == "fetch":
            uid_set = args[0]
            if uid_set == "1":
                return ("OK", [(b"1 (UID 1 RFC822 {10}", b"raw1"), b")"])
            if uid_set == "2":
                return ("NO", [None])  # persistently fails every retry
            raise AssertionError(f"unexpected uid_set {uid_set!r}")
        raise AssertionError(f"unexpected uid command {command!r}")

    provider = IMAPProvider(
        host="h", port=993, username="u", password="p", use_ssl=True,
        mailbox="INBOX", checkpoint_path=None, batch_size=1, max_retries=2,
    )
    monkeypatch.setattr(provider, "_parse_message", _fake_parse)
    provider._connection = Mock()
    provider._connection.uid.side_effect = fake_uid

    results = []
    with pytest.raises(Exception, match="UID FETCH exhausted"):
        for mail in provider.iterate_mails():
            results.append(mail)

    # batch 1 (uid 1) succeeded before batch 2 crashed — but since poll()
    # only commits once at the very end, this partial yield doesn't matter:
    # the whole run rolls back together either way.
    assert [r["imap_uid"] for r in results] == ["1"]
