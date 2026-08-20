import re

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import distinct, join, or_, select
from sqlalchemy.orm import Session

from mailextractor import models

TAG_RE = re.compile(r"^(workflow|email|run|attachment):#?(\d+)$", re.IGNORECASE)
EVENT_RE = re.compile(r"^event:(.+)$", re.IGNORECASE)
STEP_RE = re.compile(r"^step:(.+)$", re.IGNORECASE)
LEVEL_ORDER = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

def _escape_like(fragment: str) -> str:
    return (
        fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


def _apply_search_q(query, q_raw: str):
    """AND tags + free tokens (each token must appear in message or step, ILIKE)."""
    q_trim = q_raw.strip()
    if not q_trim:
        return query

    workflow_id = email_id = run_id = attachment_id = None
    event_needle: str | None = None
    step_needle: str | None = None
    free_terms: list[str] = []

    for tok in q_trim.split():
        m = TAG_RE.match(tok)
        if m:
            key, num_s = m.group(1).lower(), m.group(2)
            num = int(num_s)
            if key == "workflow":
                workflow_id = num
            elif key == "email":
                email_id = num
            elif key == "run":
                run_id = num
            elif key == "attachment":
                attachment_id = num
            continue

        m = EVENT_RE.match(tok)
        if m:
            event_needle = m.group(1)
            continue

        m = STEP_RE.match(tok)
        if m:
            step_needle = m.group(1)
            continue

        free_terms.append(tok)

    if workflow_id is not None:
        query = query.where(models.Log.workflow_id == workflow_id)
    if email_id is not None:
        query = query.where(models.Log.email_id == email_id)
    if run_id is not None:
        query = query.where(models.Log.run_id == run_id)
    if attachment_id is not None:
        query = query.where(models.Log.attachment_id == attachment_id)

    if event_needle is not None:
        esc = _escape_like(event_needle)
        query = query.where(models.Log.event_type.ilike(f"%{esc}%", escape="\\"))

    if step_needle is not None:
        esc = _escape_like(step_needle)
        query = query.where(models.Log.step.ilike(f"%{esc}%", escape="\\"))

    for word in free_terms:
        esc = _escape_like(word)
        pattern = f"%{esc}%"
        query = query.where(
            or_(
                models.Log.message.ilike(pattern, escape="\\"),
                models.Log.step.ilike(pattern, escape="\\"),
            )
        )

    return query


def get_logs(
    db: Session,
    event_type: str | None = None,
    workflow_id: str | None = None,
    email_id: str | None = None,
    run_id: str | None = None,
    attachment_id: str | None = None,
    level: str | None = None,
    run_state: str | None = None,
    q: str | None = None,
):
    query = select(models.Log)

    if run_state:
        try:
            state_enum = models.RunState[run_state]
        except KeyError:
            state_enum = None
        if state_enum is not None:
            query = query.join(models.WorkflowRun, models.Log.run_id == models.WorkflowRun.id)
            query = query.where(models.WorkflowRun.state == state_enum)

    if event_type:
        query = query.where(models.Log.event_type == event_type)
    if workflow_id:
        query = query.where(models.Log.workflow_id == int(workflow_id))
    if email_id:
        query = query.where(models.Log.email_id == int(email_id))
    if run_id:
        query = query.where(models.Log.run_id == int(run_id))
    if attachment_id:
        query = query.where(models.Log.attachment_id == int(attachment_id))
    if level:
        try:
            idx = LEVEL_ORDER.index(level)
        except ValueError:
            idx = 0
        valid_levels = [models.LogLevel[l] for l in LEVEL_ORDER[idx:]]
        query = query.where(models.Log.level.in_(valid_levels))

    if q:
        query = _apply_search_q(query, q)

    query = query.order_by(models.Log.created_at.desc())

    return paginate(db, query)


def get_log_filters(db: Session, run_id: str | None = None):
    query = select(distinct(models.Log.event_type))
    if run_id:
        query = query.where(models.Log.run_id == int(run_id))
    return db.execute(query).scalars().all()
