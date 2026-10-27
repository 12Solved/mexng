"""scripts/check_logs.py rule matching, queueing and cursor progression."""
from datetime import datetime

import pytest

import scripts.check_logs as check_logs
from mailextractor.models import AlertQueue, AlertRule, AlertScanState, Checkpoint, Log, LogLevel, User, WorkflowModel


@pytest.fixture(autouse=True)
def scan_state(db_session):
    # Seeded by the migration in a real db; the test db is built with create_all.
    db_session.add(AlertScanState(id=1, last_log_id=0))
    db_session.commit()


@pytest.fixture
def run_scan(make_config, test_engine):
    # No safety margin: test logs are committed before the scan starts.
    return lambda **kw: check_logs.check_once(make_config(), engine=test_engine, **{"safety_margin_seconds": 0, **kw})


@pytest.fixture
def make_user(db_session):
    def _make(name="alice"):
        user = User(name=name, email=f"{name}@example.com")
        db_session.add(user)
        db_session.commit()
        return user
    return _make


def _add_rule(db_session, user, **filters):
    rule = AlertRule(user_id=user.id, **filters)
    db_session.add(rule)
    db_session.commit()
    return rule


def _add_log(db_session, event_type="WORKFLOW_FAILED", level=LogLevel.ERROR, **fields):
    log = Log(level=level, event_type=event_type, message="msg", **fields)
    db_session.add(log)
    db_session.commit()
    return log


def _queued(db_session):
    db_session.expire_all()
    return sorted((row.user_id, row.log_id) for row in db_session.query(AlertQueue))


def _cursor(db_session):
    db_session.expire_all()
    return db_session.get(AlertScanState, 1).last_log_id


def test_matching_log_is_queued_once(db_session, run_scan, make_user):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    log = _add_log(db_session)

    run_scan()
    run_scan()

    assert _queued(db_session) == [(user.id, log.id)]


def test_min_level_threshold(db_session, run_scan, make_user):
    user = make_user()
    _add_rule(db_session, user, min_level=LogLevel.ERROR)
    run_scan()
    _add_log(db_session, level=LogLevel.WARNING)
    error = _add_log(db_session, level=LogLevel.ERROR)
    critical = _add_log(db_session, level=LogLevel.CRITICAL)

    run_scan()

    assert _queued(db_session) == [(user.id, error.id), (user.id, critical.id)]


def test_filters_match_exact_or_any(db_session, run_scan, make_user):
    user = make_user()
    workflow = WorkflowModel(name="wf", workflow_json={})
    checkpoint = Checkpoint(
        name="cp", reference_timestamp=datetime(2026, 1, 1), normal_interval_hours=24,
        next_expected_at=datetime(2026, 1, 2),
    )
    db_session.add_all([workflow, checkpoint])
    db_session.commit()
    _add_rule(db_session, user, event_type="CHECKPOINT_MISSED", checkpoint_id=checkpoint.id)
    _add_rule(db_session, user, workflow_id=workflow.id)
    run_scan()

    hit_checkpoint = _add_log(db_session, "CHECKPOINT_MISSED", LogLevel.WARNING, checkpoint_id=checkpoint.id)
    _add_log(db_session, "CHECKPOINT_MISSED", LogLevel.WARNING)  # wrong checkpoint
    _add_log(db_session, "OTHER_EVENT", checkpoint_id=checkpoint.id)  # wrong event type
    hit_workflow = _add_log(db_session, "ANY_EVENT", workflow_id=workflow.id)

    run_scan()

    assert _queued(db_session) == [(user.id, hit_checkpoint.id), (user.id, hit_workflow.id)]


def test_disabled_rule_is_ignored(db_session, run_scan, make_user):
    user = make_user()
    _add_rule(db_session, user, enabled=False)
    run_scan()
    _add_log(db_session)

    run_scan()

    assert _queued(db_session) == []


def test_overlapping_rules_queue_once_per_user(db_session, run_scan, make_user):
    alice, bob = make_user("alice"), make_user("bob")
    _add_rule(db_session, alice)
    _add_rule(db_session, alice, event_type="WORKFLOW_FAILED")
    _add_rule(db_session, bob, event_type="WORKFLOW_FAILED")
    run_scan()
    log = _add_log(db_session)

    run_scan()

    assert _queued(db_session) == [(alice.id, log.id), (bob.id, log.id)]


def test_own_events_are_not_queued(db_session, run_scan, make_user):
    user = make_user()
    _add_rule(db_session, user, min_level=LogLevel.DEBUG)
    run_scan()
    _add_log(db_session, "CHECK_LOGS_FAILED")

    run_scan()

    assert _queued(db_session) == []


def test_young_log_blocks_cursor(db_session, run_scan, make_user):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    start = _cursor(db_session)
    _add_log(db_session)  # created now: inside the margin
    _add_log(db_session, created_at=datetime(2000, 1, 1))  # older, higher id

    run_scan(safety_margin_seconds=60)

    # The older row isn't scanned past the younger one it follows.
    assert _queued(db_session) == []
    assert _cursor(db_session) == start
