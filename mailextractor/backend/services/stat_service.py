from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, Boolean

from mailextractor.models import Email, WorkflowRun, WorkflowModel, Checkpoint, Log, RunState, LogLevel

VALID_PRESETS = frozenset({"last_24h", "last_7d", "last_28d", "all"})


def normalize_period(period: str | None) -> str:
    if not period or period.strip().lower() == "all":
        return "all"
    p = period.strip().lower()
    return p if p in VALID_PRESETS else "all"


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def period_window(preset: str) -> tuple[datetime | None, datetime | None, datetime | None]:
    """
    Returns (start_inclusive, end_exclusive, display_end) as naive UTC.
    When end_exclusive is None, upper bound is \"now\" in queries.
    display_end is included in API metadata for clients.
    """
    now = _utc_now_naive()

    if preset == "all":
        return None, None, now

    if preset == "last_24h":
        return now - timedelta(hours=24), None, now

    if preset == "last_7d":
        return now - timedelta(days=7), None, now

    if preset == "last_28d":
        return now - timedelta(days=28), None, now

    return None, None, now


def _email_count_in_range(db: Session, start: datetime | None, end_exclusive: datetime | None) -> int:
    q = db.query(func.count(Email.id))
    if start is not None:
        q = q.filter(Email.created_at >= start)
    if end_exclusive is not None:
        q = q.filter(Email.created_at < end_exclusive)
    else:
        q = q.filter(Email.created_at <= _utc_now_naive())
    return q.scalar() or 0


def _latest_runs_by_state(
    db: Session, start: datetime | None, end_exclusive: datetime | None, workflow_ids: list[int] | None = None
) -> dict[RunState, int]:
    """
    Counts the latest run per (email_id, workflow_id) by state.
    Only considers runs in [start, end); end open means up to now.
    """
    from sqlalchemy import and_

    # Subquery to find the max run ID for each (email_id, workflow_id) pair
    max_run_subq = db.query(
        WorkflowRun.email_id,
        WorkflowRun.workflow_id,
        func.max(WorkflowRun.id).label("max_id"),
    ).filter(~WorkflowRun.run_options.contains({"@dry_run": True}))
    
    if start is not None:
        max_run_subq = max_run_subq.filter(WorkflowRun.created_at >= start)
    if end_exclusive is not None:
        max_run_subq = max_run_subq.filter(WorkflowRun.created_at < end_exclusive)
    else:
        max_run_subq = max_run_subq.filter(WorkflowRun.created_at <= _utc_now_naive())

    if workflow_ids is not None:
        max_run_subq = max_run_subq.filter(WorkflowRun.workflow_id.in_(workflow_ids))

    max_run_subq = max_run_subq.group_by(
        WorkflowRun.email_id, WorkflowRun.workflow_id
    ).subquery()

    # Join back to get the state of those latest runs
    rows = db.query(WorkflowRun.state, func.count(WorkflowRun.id)).join(
        max_run_subq,
        and_(
            WorkflowRun.id == max_run_subq.c.max_id,
            WorkflowRun.email_id == max_run_subq.c.email_id,
            WorkflowRun.workflow_id == max_run_subq.c.workflow_id,
        ),
    ).group_by(WorkflowRun.state).all()

    return {state: count for state, count in rows}


def _running_count_latest(db: Session) -> int:
    """Count latest runs that are in running state."""
    from sqlalchemy import and_

    max_run_subq = db.query(
        WorkflowRun.email_id,
        WorkflowRun.workflow_id,
        func.max(WorkflowRun.id).label("max_id"),
    ).filter(~WorkflowRun.run_options.contains({"@dry_run": True})).group_by(
        WorkflowRun.email_id, WorkflowRun.workflow_id
    ).subquery()

    return db.query(func.count(WorkflowRun.id)).join(
        max_run_subq,
        and_(
            WorkflowRun.id == max_run_subq.c.max_id,
            WorkflowRun.email_id == max_run_subq.c.email_id,
            WorkflowRun.workflow_id == max_run_subq.c.workflow_id,
        ),
    ).filter(WorkflowRun.state == RunState.running).scalar() or 0


def get_stats(db: Session, period: str | None = None) -> dict[str, Any]:
    preset = normalize_period(period)
    start, end_excl, display_end = period_window(preset)

    total_emails = db.query(func.count(Email.id)).scalar() or 0
    emails_in_period = total_emails if preset == "all" else _email_count_in_range(db, start, end_excl)

    if preset == "all":
        run_by_state = _latest_runs_by_state(db, None, None)
    else:
        run_by_state = _latest_runs_by_state(db, start, end_excl)
        # For non-"all" periods, running count is global latest runs
        running_count = _running_count_latest(db)
        run_by_state[RunState.running] = running_count

    runs_payload = {
        "success": run_by_state.get(RunState.success, 0),
        "failed": run_by_state.get(RunState.failed, 0),
        "running": run_by_state.get(RunState.running, 0),
        "skipped": run_by_state.get(RunState.skipped, 0),
        "re_run": run_by_state.get(RunState.re_run, 0),
    }

    total_workflows = db.query(func.count(WorkflowModel.id)).scalar() or 0
    enabled_workflows = (
        db.query(func.count(WorkflowModel.id))
        .filter(WorkflowModel.enabled == True)  # noqa: E712
        .scalar()
        or 0
    )

    checkpoint_counts: dict = dict(
        db.query(Checkpoint.status, func.count(Checkpoint.id))
        .group_by(Checkpoint.status)
        .all()
    )

    err_q = db.query(Log).filter(Log.level == LogLevel.ERROR)
    if start is not None:
        err_q = err_q.filter(Log.created_at >= start)
    if end_excl is not None:
        err_q = err_q.filter(Log.created_at < end_excl)
    elif preset != "all":
        err_q = err_q.filter(Log.created_at <= _utc_now_naive())

    recent_errors = err_q.order_by(Log.created_at.desc()).limit(10).all()

    starts_at_iso = start.isoformat() + "Z" if start else None
    if end_excl is not None:
        ends_at_iso = end_excl.isoformat() + "Z"
    else:
        ends_at_iso = display_end.isoformat() + "Z" if display_end else None

    return {
        "period": {
            "preset": preset,
            "starts_at": starts_at_iso,
            "ends_at": ends_at_iso,
        },
        "emails": {"total": total_emails, "in_period": emails_in_period},
        "runs": runs_payload,
        "workflows": {"total": total_workflows, "enabled": enabled_workflows},
        "checkpoints": {
            "ok": checkpoint_counts.get("ok", 0),
            "missed": checkpoint_counts.get("missed", 0),
            "never_seen": checkpoint_counts.get("never_seen", 0),
        },
        "recent_errors": [
            {
                "id": e.id,
                "message": e.message,
                "step": e.step,
                "event_type": e.event_type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "email_id": e.email_id,
                "workflow_id": e.workflow_id,
            }
            for e in recent_errors
        ],
    }
