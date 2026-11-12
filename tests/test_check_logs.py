"""scripts/check_logs.py rule matching, queueing, cursor progression and digest sending."""
from datetime import datetime, timedelta

import pytest

import scripts.check_logs as check_logs
from mailextractor.models import (
    AlertQueue, AlertRule, AlertScanState, Attachment, Checkpoint, Email, Log, LogLevel, RunState, User,
    WorkflowModel, WorkflowRun,
)


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


def _add_log(db_session, event_type="WORKFLOW_FAILED", level=LogLevel.ERROR, message="msg", **fields):
    log = Log(level=level, event_type=event_type, message=message, **fields)
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


class FakeNotify(list):
    """Records digests instead of sending; `result` is what notify() returns."""
    result = True

    def __call__(self, subject, body, recipients=None, meta=None, html=None):
        self.append({"subject": subject, "body": body, "recipients": recipients, "html": html})
        return self.result


@pytest.fixture
def sent_digests(monkeypatch):
    fake = FakeNotify()
    monkeypatch.setattr(check_logs, "notify", fake)
    return fake


def _age_queue(db_session, minutes):
    db_session.query(AlertQueue).update(
        {"queued_at": AlertQueue.queued_at - timedelta(minutes=minutes)}, synchronize_session=False
    )
    db_session.commit()


def _unsent(db_session):
    db_session.expire_all()
    return sorted((row.user_id, row.log_id) for row in db_session.query(AlertQueue).filter(AlertQueue.sent_at.is_(None)))


def test_digest_waits_for_collection_window(db_session, run_scan, make_user, sent_digests):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    log = _add_log(db_session)

    run_scan()

    assert sent_digests == []
    assert _unsent(db_session) == [(user.id, log.id)]


def test_digest_sent_once_window_passes(db_session, run_scan, make_user, sent_digests):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    first = _add_log(db_session, message="first")
    second = _add_log(db_session, message="second")
    run_scan()
    _age_queue(db_session, 11)

    run_scan()
    run_scan()

    assert len(sent_digests) == 1
    assert sent_digests[0]["recipients"] == ["alice@example.com"]
    assert sent_digests[0]["subject"] == "[mexng] 2 alert(s)"
    assert "first" in sent_digests[0]["body"] and "second" in sent_digests[0]["body"]
    assert _unsent(db_session) == []
    assert _queued(db_session) == [(user.id, first.id), (user.id, second.id)]


def test_digest_per_user(db_session, run_scan, make_user, sent_digests):
    alice, bob = make_user("alice"), make_user("bob")
    _add_rule(db_session, alice, event_type="A_EVENT")
    _add_rule(db_session, bob, event_type="B_EVENT")
    run_scan()
    _add_log(db_session, "A_EVENT", message="for alice")
    _add_log(db_session, "B_EVENT", message="for bob")
    run_scan()
    _age_queue(db_session, 11)

    run_scan()

    by_recipient = {call["recipients"][0]: call["body"] for call in sent_digests}
    assert set(by_recipient) == {"alice@example.com", "bob@example.com"}
    assert "for alice" in by_recipient["alice@example.com"] and "for bob" not in by_recipient["alice@example.com"]
    assert "for bob" in by_recipient["bob@example.com"] and "for alice" not in by_recipient["bob@example.com"]


def test_user_without_email_is_skipped(db_session, run_scan, sent_digests):
    user = User(name="noemail")
    db_session.add(user)
    db_session.commit()
    _add_rule(db_session, user)
    run_scan()
    log = _add_log(db_session)
    run_scan()
    _age_queue(db_session, 11)

    run_scan()

    assert sent_digests == []
    assert _unsent(db_session) == [(user.id, log.id)]


def test_failed_digest_stays_unsent_and_retries(db_session, run_scan, make_user, sent_digests):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    log = _add_log(db_session)
    run_scan()
    _age_queue(db_session, 11)
    sent_digests.result = False

    run_scan()

    assert len(sent_digests) == 1
    assert _unsent(db_session) == [(user.id, log.id)]

    sent_digests.result = True
    run_scan()

    assert len(sent_digests) == 2
    assert _unsent(db_session) == []


def test_logs_after_digest_start_new_window(db_session, run_scan, make_user, sent_digests):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    _add_log(db_session)
    run_scan()
    _age_queue(db_session, 11)
    run_scan()
    later = _add_log(db_session)

    run_scan()

    assert len(sent_digests) == 1
    assert _unsent(db_session) == [(user.id, later.id)]


def test_window_is_configurable(db_session, run_scan, make_user, sent_digests):
    user = make_user()
    _add_rule(db_session, user)
    run_scan()
    _add_log(db_session)
    run_scan()
    _age_queue(db_session, 3)

    run_scan()
    assert sent_digests == []

    run_scan(collection_window_minutes=2)
    assert len(sent_digests) == 1


PUBLIC_URL = "https://mexng.example.com/app/"


@pytest.fixture
def send_digest(db_session, make_config, test_engine, make_user, sent_digests):
    """Queues the given log fields for one user, ages the queue and returns the digest body."""
    def _send(public_url=PUBLIC_URL, **log_fields):
        user = make_user()
        _add_rule(db_session, user)
        scan = lambda: check_logs.check_once(
            make_config(APP_PUBLIC_URL=public_url), engine=test_engine, safety_margin_seconds=0
        )
        scan()
        _add_log(db_session, **log_fields)
        scan()
        _age_queue(db_session, 11)
        scan()
        assert len(sent_digests) == 1
        return sent_digests[0]["body"]
    return _send


def _add_linked_entities(db_session, subject="Your March invoice"):
    workflow = WorkflowModel(name="Invoices", workflow_json={})
    email = Email(subject=subject)
    db_session.add_all([workflow, email])
    db_session.commit()
    run = WorkflowRun(workflow_id=workflow.id, email_id=email.id, state=RunState.failed)
    attachment = Attachment(email_id=email.id, filename="invoice.pdf")
    db_session.add_all([run, attachment])
    db_session.commit()
    return dict(workflow_id=workflow.id, email_id=email.id, run_id=run.id, attachment_id=attachment.id)


def test_digest_links_each_mentioned_view(db_session, send_digest, sent_digests):
    ids = _add_linked_entities(db_session)

    body = send_digest(**ids)

    base = "https://mexng.example.com/app"
    wf, em, run, att = ids["workflow_id"], ids["email_id"], ids["run_id"], ids["attachment_id"]
    assert f"  Workflow: Invoices (#{wf})  {base}/workflow/{wf}" in body
    assert f'  Email: "Your March invoice" (#{em})  {base}/email/{em}' in body
    assert f"  Run #{run} logs  {base}/logs?q=run:{run}" in body
    assert f"  Attachment #{att} logs  {base}/logs?q=attachment:{att}" in body

    html = sent_digests[0]["html"]
    assert f'<a href="{base}/workflow/{wf}" style="color:#2563eb">Workflow: Invoices (#{wf})</a>' in html
    assert f'href="{base}/email/{em}" style="color:#2563eb">Email: &quot;Your March invoice&quot; (#{em})</a>' in html
    assert f'href="{base}/logs?q=run:{run}"' in html
    assert f'href="{base}/logs?q=attachment:{att}"' in html


def test_digest_links_only_mentioned_views(db_session, send_digest):
    workflow = WorkflowModel(name="Invoices", workflow_json={})
    db_session.add(workflow)
    db_session.commit()

    body = send_digest(workflow_id=workflow.id)

    assert "/workflow/" in body
    assert "Email:" not in body and "Run #" not in body and "Attachment #" not in body


def test_digest_email_without_subject_shows_id(db_session, send_digest):
    ids = _add_linked_entities(db_session, subject=None)

    body = send_digest(email_id=ids["email_id"])

    assert f"  Email: (#{ids['email_id']})  https://mexng.example.com/app/email/{ids['email_id']}" in body


def test_digest_has_no_links_without_public_url(db_session, send_digest, sent_digests):
    ids = _add_linked_entities(db_session)

    body = send_digest(public_url="", **ids)

    assert "http" not in body
    assert len(body.splitlines()) == 1
    # HTML still names everything the log mentions, just unlinked.
    html = sent_digests[0]["html"]
    assert "<a " not in html
    assert f"Workflow: Invoices (#{ids['workflow_id']})" in html
    assert f"Run #{ids['run_id']} logs" in html


def test_html_digest_escapes_db_values(db_session, send_digest, sent_digests):
    ids = _add_linked_entities(db_session, subject="<b>hi</b>")

    send_digest(email_id=ids["email_id"], message="<script>x</script>")

    html = sent_digests[0]["html"]
    assert "<script>" not in html and "<b>hi</b>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "&lt;b&gt;hi&lt;/b&gt;" in html
