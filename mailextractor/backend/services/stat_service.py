from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, Boolean

from mailextractor.models import Email, WorkflowRun, WorkflowModel, Checkpoint, Log, RunState, LogLevel

VALID_PRESETS = frozenset({"last_24h", "last_7d", "last_28d", "all"})
RECENT_RUNS_LIMIT = 20


def normalize_period(period: str | None) -> str:
    if not period or period.strip().lower() == "all":
        return "all"
    p = period.strip().lower()
    return p if p in VALID_PRESETS else "all"


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso_utc(dt: datetime | None) -> str | None:
    """Serialize a naive-UTC timestamp with a "Z" so browsers don't read it as local time."""
    return dt.isoformat() + "Z" if dt else None


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


def normalize_run_state(state: str | None) -> RunState | None:
    """Unknown or empty values mean no filter, like an unknown period means "all"."""
    try:
        return RunState(state.strip().lower()) if state else None
    except ValueError:
        return None


def _recent_runs(db: Session, state: RunState | None) -> list[dict[str, Any]]:
    """Newest non-dry runs, optionally in one state, regardless of the selected period."""
    query = (
        db.query(WorkflowRun, WorkflowModel.name, Email.subject)
        .join(WorkflowModel, WorkflowRun.workflow_id == WorkflowModel.id)
        .outerjoin(Email, WorkflowRun.email_id == Email.id)
        .filter(~WorkflowRun.run_options.contains({"@dry_run": True}))
    )
    if state is not None:
        query = query.filter(WorkflowRun.state == state)
    rows = (
        query
        .order_by(WorkflowRun.id.desc())
        .limit(RECENT_RUNS_LIMIT)
        .all()
    )
    return [
        {
            "id": run.id,
            "state": run.state.value,
            "workflow_id": run.workflow_id,
            "workflow_name": workflow_name,
            "email_id": run.email_id,
            "email_subject": email_subject,
            "created_at": _iso_utc(run.created_at),
        }
        for run, workflow_name, email_subject in rows
    ]


def get_stats(db: Session, period: str | None = None, runs_state: str | None = None) -> dict[str, Any]:
    preset = normalize_period(period)
    start, end_excl, display_end = period_window(preset)
    recent_state = normalize_run_state(runs_state)

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

    starts_at_iso = _iso_utc(start)
    ends_at_iso = _iso_utc(end_excl if end_excl is not None else display_end)

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
        # Echoed back so the client can tell whether recent_runs matches its selected filter yet.
        "recent_runs_state": recent_state.value if recent_state else None,
        "recent_runs": _recent_runs(db, recent_state),
        "recent_errors": [
            {
                "id": e.id,
                "message": e.message,
                "step": e.step,
                "event_type": e.event_type,
                "created_at": _iso_utc(e.created_at),
                "email_id": e.email_id,
                "workflow_id": e.workflow_id,
            }
            for e in recent_errors
        ],
    }
