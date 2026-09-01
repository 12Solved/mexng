"""IMAPProvider._fetch_uids never checked the status returned by UID SEARCH
and re-raised on any exception instead of degrading gracefully, unlike its
sibling FETCH step (which retries with backoff). A SEARCH failure is an
infrastructure/transient problem, not a data problem, so it should degrade
to "no new mail this cycle" (checkpoint doesn't move, nothing lost) rather
than crashing the whole poll — matching FETCH's retry treatment.
"""
from unittest.mock import Mock

from mailextractor.app.poller import provider as provider_module
from mailextractor.app.poller.provider import IMAPProvider


def _provider(monkeypatch, max_retries=3):
    monkeypatch.setattr(provider_module.time, "sleep", lambda _: None)  # skip real backoff delays
    provider = IMAPProvider(
        host="h", port=993, username="u", password="p", use_ssl=True,
        mailbox="INBOX", checkpoint_path=None, max_retries=max_retries,
    )
    provider._connection = Mock()
    return provider


def test_search_non_ok_status_degrades_to_empty_list_after_retries(monkeypatch):
    provider = _provider(monkeypatch, max_retries=3)
    provider._connection.uid.return_value = ("NO", [None])

    uids = provider._fetch_uids(None)  # must NOT raise

    assert uids == []
    assert provider._connection.uid.call_count == 3


def test_search_exception_degrades_to_empty_list_after_retries(monkeypatch):
    provider = _provider(monkeypatch, max_retries=3)
    provider._connection.uid.side_effect = Exception("connection reset")

    uids = provider._fetch_uids(None)  # must NOT raise

    assert uids == []
    assert provider._connection.uid.call_count == 3


def test_search_recovers_after_a_transient_failure(monkeypatch):
    provider = _provider(monkeypatch, max_retries=3)
    provider._connection.uid.side_effect = [
        ("NO", [None]),
        ("OK", [b"1 2 3"]),
    ]

    uids = provider._fetch_uids(None)

    assert uids == [1, 2, 3]
    assert provider._connection.uid.call_count == 2
