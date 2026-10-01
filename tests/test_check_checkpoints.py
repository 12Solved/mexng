"""scripts/check_checkpoints.py status progression.

Regression: a missed checkpoint flipped back to "ok" on the very next check,
because once next_expected_at was rolled forward the open-window branch
returned "ok" for anything ever seen. Also: the miss alert reported the
rolled-forward deadline instead of the one actually missed."""
from datetime import datetime, timedelta, timezone

import pytest

import scripts.check_checkpoints as check_checkpoints
from mailextractor.models import Checkpoint


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(check_checkpoints, "notify", lambda **kwargs: calls.append(kwargs))
    return calls


@pytest.fixture
def run_check(make_config, test_engine):
    return lambda: check_checkpoints.check_once(make_config(), engine=test_engine)


def _add_checkpoint(db_session, **overrides):
    now = _utcnow()
    fields = dict(
        name="cp",
        reference_timestamp=now - timedelta(days=10),
        normal_interval_hours=24,
        late_interval_hours=1,
        next_expected_at=now - timedelta(minutes=5),
        last_seen_at=now - timedelta(days=3),
        status="ok",
    )
    fields.update(overrides)
    cp = Checkpoint(**fields)
    db_session.add(cp)
    db_session.commit()
    return cp


def test_missed_checkpoint_stays_missed_while_nothing_arrives(db_session, run_check, sent):
    cp = _add_checkpoint(db_session)

    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"

    # Next check: the late window is open and still empty.
    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"


def test_miss_alert_reports_the_missed_deadline(db_session, run_check, sent):
    cp = _add_checkpoint(db_session)
    missed_deadline = cp.next_expected_at

    run_check()

    assert len(sent) == 1
    assert str(missed_deadline) in sent[0]["body"]


def test_arrival_after_miss_turns_ok_while_window_open(db_session, run_check, sent):
    cp = _add_checkpoint(db_session)
    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"

    cp.last_seen_at = _utcnow()
    db_session.commit()
    run_check()

    db_session.refresh(cp)
    assert cp.status == "ok"


def test_every_missed_window_alerts(db_session, run_check, sent):
    cp = _add_checkpoint(db_session)
    run_check()

    # Simulate the late window closing with still nothing seen.
    cp.next_expected_at = _utcnow() - timedelta(minutes=1)
    db_session.commit()
    run_check()

    db_session.refresh(cp)
    assert cp.status == "missed"
    assert len(sent) == 2


def test_on_time_arrival_is_ok_and_snaps_to_grid(db_session, run_check, sent):
    now = _utcnow()
    reference = now - timedelta(days=10, minutes=5)
    cp = _add_checkpoint(
        db_session,
        reference_timestamp=reference,
        next_expected_at=now - timedelta(minutes=5),
        last_seen_at=now - timedelta(hours=2),
    )

    run_check()

    db_session.refresh(cp)
    assert cp.status == "ok"
    assert cp.next_expected_at == reference + timedelta(days=11)
    assert sent == []
