"""scripts/check_checkpoints.py status progression.

Regression: a missed checkpoint flipped back to "ok" on the very next check,
because once next_expected_at was rolled forward the open-window branch
returned "ok" for anything ever seen. Also: the miss alert reported the
rolled-forward deadline instead of the one actually missed."""
import logging
from datetime import datetime, timedelta, timezone

import pytest

import scripts.check_checkpoints as check_checkpoints
from mailextractor.models import Checkpoint


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def missed():
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            if getattr(record, "event_type", None) == "CHECKPOINT_MISSED":
                records.append(record)

    handler = _Capture()
    check_checkpoints.logger.addHandler(handler)
    yield records
    check_checkpoints.logger.removeHandler(handler)


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


def test_missed_checkpoint_stays_missed_while_nothing_arrives(db_session, run_check, missed):
    cp = _add_checkpoint(db_session)

    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"

    # Next check: the late window is open and still empty.
    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"


def test_miss_log_reports_the_missed_deadline(db_session, run_check, missed):
    cp = _add_checkpoint(db_session)
    missed_deadline = cp.next_expected_at

    run_check()

    assert len(missed) == 1
    assert str(missed_deadline) in missed[0].getMessage()


def test_arrival_after_miss_turns_ok_while_window_open(db_session, run_check, missed):
    cp = _add_checkpoint(db_session)
    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"

    cp.last_seen_at = _utcnow()
    db_session.commit()
    run_check()

    db_session.refresh(cp)
    assert cp.status == "ok"


def test_every_missed_window_is_logged(db_session, run_check, missed):
    cp = _add_checkpoint(db_session)
    run_check()

    # Simulate the late window closing with still nothing seen.
    cp.next_expected_at = _utcnow() - timedelta(minutes=1)
    db_session.commit()
    run_check()

    db_session.refresh(cp)
    assert cp.status == "missed"
    assert len(missed) == 2


def test_on_time_arrival_is_ok_and_snaps_to_grid(db_session, run_check, missed):
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
    assert missed == []


@pytest.fixture
def clock(monkeypatch):
    class _Clock(datetime):
        current = _utcnow()

        @classmethod
        def now(cls, tz=None):
            return cls.current.replace(tzinfo=tz)

    monkeypatch.setattr(check_checkpoints, "datetime", _Clock)
    return _Clock


def test_late_arrival_counts_when_late_interval_exceeds_normal(db_session, run_check, missed, clock):
    t0 = clock.current
    cp = _add_checkpoint(
        db_session,
        reference_timestamp=t0 - timedelta(days=10),
        normal_interval_hours=1,
        late_interval_hours=24,
        next_expected_at=t0 - timedelta(minutes=5),
        last_seen_at=t0 - timedelta(days=3),
    )
    run_check()
    assert len(missed) == 1

    clock.current += timedelta(hours=10)
    cp.last_seen_at = clock.current
    db_session.commit()

    clock.current += timedelta(hours=15)
    run_check()

    db_session.refresh(cp)
    assert cp.status == "ok"
    assert len(missed) == 1


def test_late_arrival_does_not_satisfy_next_window(db_session, run_check, missed, clock):
    t0 = clock.current
    cp = _add_checkpoint(
        db_session,
        reference_timestamp=t0 - timedelta(days=10, minutes=5),
        normal_interval_hours=24,
        late_interval_hours=1,
        next_expected_at=t0 - timedelta(minutes=5),
        last_seen_at=t0 - timedelta(days=3),
    )
    run_check()

    clock.current += timedelta(minutes=30)
    cp.last_seen_at = clock.current
    db_session.commit()

    clock.current += timedelta(minutes=30)
    run_check()
    db_session.refresh(cp)
    assert cp.status == "ok"
    assert cp.next_expected_at == t0 - timedelta(minutes=5) + timedelta(days=1)

    clock.current += timedelta(days=1)
    run_check()
    db_session.refresh(cp)
    assert cp.status == "missed"
    assert len(missed) == 2


def test_downtime_yields_a_single_miss(db_session, run_check, missed, clock):
    t0 = clock.current
    cp = _add_checkpoint(
        db_session,
        reference_timestamp=t0 - timedelta(days=10),
        normal_interval_hours=1,
        late_interval_hours=1,
        next_expected_at=t0 - timedelta(days=2),
        last_seen_at=t0 - timedelta(days=3),
    )
    missed_deadline = cp.next_expected_at

    run_check()
    run_check()

    db_session.refresh(cp)
    assert cp.status == "missed"
    assert t0 < cp.next_expected_at <= t0 + timedelta(hours=1)
    assert len(missed) == 1
    assert str(missed_deadline) in missed[0].getMessage()
