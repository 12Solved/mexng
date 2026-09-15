"""_run_loop()'s job() used to catch every poll() failure identically —
logged and retried next interval, no distinction between a one-off
poison-pill (fine) and something persistent like expired IMAP credentials or
a dead DB (retries forever with no operator-visible signal). LoopFailureTracker
tracks consecutive failures and escalates the log level once they cross the
threshold, resetting on any success."""
from unittest.mock import Mock

from mailextractor.app.poller.poller import CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD, LoopFailureTracker


def _failing():
    raise Exception("boom")


def test_failures_below_threshold_log_at_exception_level_not_critical():
    logger = Mock()
    tracker = LoopFailureTracker(logger)

    for _ in range(CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD - 1):
        tracker.run(_failing)

    assert logger.exception.call_count == CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD - 1
    assert logger.critical.call_count == 0


def test_reaching_threshold_escalates_to_critical():
    logger = Mock()
    tracker = LoopFailureTracker(logger)

    for _ in range(CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD):
        tracker.run(_failing)

    assert logger.critical.call_count == 1
    _, kwargs = logger.critical.call_args
    assert kwargs["extra"]["consecutive_failures"] == CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD


def test_every_failure_past_threshold_keeps_escalating():
    logger = Mock()
    tracker = LoopFailureTracker(logger)

    for _ in range(CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD + 2):
        tracker.run(_failing)

    assert logger.critical.call_count == 3  # threshold, +1, +2


def test_success_resets_the_streak():
    logger = Mock()
    tracker = LoopFailureTracker(logger)

    for _ in range(CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD - 1):
        tracker.run(_failing)
    tracker.run(lambda: None)  # success
    assert tracker.consecutive_failures == 0

    tracker.run(_failing)  # only 1 failure since the reset
    assert logger.critical.call_count == 0
