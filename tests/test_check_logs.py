"""scripts/check_logs.py alert digest and watermark progression."""
import pytest

import scripts.check_logs as check_logs
from mailextractor.models import Log, LogLevel


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(check_logs, "notify", lambda **kwargs: calls.append(kwargs))
    return calls


@pytest.fixture
def run_check(make_config, test_engine, tmp_path):
    state_file = str(tmp_path / "check_logs_state.json")
    return lambda: check_logs.check_once(state_file, make_config(), engine=test_engine)


def _add_log(db_session, event_type, level=LogLevel.ERROR, message="msg"):
    db_session.add(Log(level=level, event_type=event_type, message=message))
    db_session.commit()


def test_first_run_skips_existing_history(db_session, run_check, sent):
    _add_log(db_session, "WORKFLOW_FAILED")

    run_check()

    assert sent == []


def test_digest_lists_each_alert_row(db_session, run_check, sent):
    run_check()
    _add_log(db_session, "CHECKPOINT_MISSED", LogLevel.WARNING, "Checkpoint 'a' missed")
    _add_log(db_session, "CHECKPOINT_MISSED", LogLevel.WARNING, "Checkpoint 'b' missed")
    _add_log(db_session, "SOME_OTHER_EVENT", message="not alert-worthy")

    run_check()

    assert len(sent) == 1
    assert sent[0]["meta"] == {"count": 2}
    assert "Checkpoint 'a' missed" in sent[0]["body"]
    assert "Checkpoint 'b' missed" in sent[0]["body"]
    assert "not alert-worthy" not in sent[0]["body"]


def test_alert_rows_are_sent_once(db_session, run_check, sent):
    run_check()
    _add_log(db_session, "WORKFLOW_FAILED")

    run_check()
    run_check()

    assert len(sent) == 1
