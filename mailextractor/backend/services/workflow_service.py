from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, select, cast, String, or_, and_
from sqlalchemy.orm import Session

from mailextractor import models
from mailextractor.backend import schemas
from mailextractor.users import get_default_user


def get_workflows(db: Session, q: str | None = None):
    query = select(models.WorkflowModel).order_by(models.WorkflowModel.id.desc())
    # search in both name and workflow_json for the provided query string
    if q:
        json_text = cast(models.WorkflowModel.workflow_json, String)
        query = query.where(
            or_(
                models.WorkflowModel.name.ilike(f"%{q}%"),
                json_text.ilike(f"%{q}%")
            )
        )

    page = paginate(db, query)

    workflow_ids = [wf.id for wf in page.items]
    stats: dict[int, dict[str, int]] = {}
    if workflow_ids:
        # Subquery to find the max run ID for each (email_id, workflow_id) pair
        max_run_subq = db.query(
            models.WorkflowRun.email_id,
            models.WorkflowRun.workflow_id,
            func.max(models.WorkflowRun.id).label('max_id')
        ).filter(
            models.WorkflowRun.workflow_id.in_(workflow_ids),
            ~models.WorkflowRun.run_options.contains({"@dry_run": True})
        ).group_by(
            models.WorkflowRun.email_id, 
            models.WorkflowRun.workflow_id
        ).subquery()
        
        # Join back to get the state of those latest runs and count by workflow
        rows = db.query(
            models.WorkflowRun.workflow_id,
            models.WorkflowRun.state,
            func.count().label("count"),
        ).join(
            max_run_subq,
            and_(
                models.WorkflowRun.id == max_run_subq.c.max_id,
                models.WorkflowRun.email_id == max_run_subq.c.email_id,
                models.WorkflowRun.workflow_id == max_run_subq.c.workflow_id
            )
        ).group_by(
            models.WorkflowRun.workflow_id, 
            models.WorkflowRun.state
        ).all()

        for workflow_id, state, count in rows:
            stats.setdefault(workflow_id, {})[state.value] = count

    items = []
    for wf in page.items:
        schema = schemas.WorkflowSchema.model_validate(wf)
        wf_stats = stats.get(wf.id, {})
        schema.run_stats = schemas.WorkflowRunSummary(
            success=wf_stats.get("success", 0),
            failed=wf_stats.get("failed", 0),
            skipped=wf_stats.get("skipped", 0),
            re_run=wf_stats.get("re_run", 0),
        )
        items.append(schema)

    page.items = items
    return page


def get_workflow(db: Session, workflow_id: int):
    return db.query(models.WorkflowModel).filter(models.WorkflowModel.id == workflow_id).first()


def create_workflow(db: Session, name: str, workflow_json: dict, description: str | None = None, user_id: int | None = None):
    if user_id is None:
        user_id = get_default_user(db).id
    workflow = models.WorkflowModel(name=name, workflow_json=workflow_json, description=description, user_id=user_id)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def update_workflow(db: Session, workflow_id: int, name: str, workflow_json: dict, description: str | None = None):
    workflow = db.query(models.WorkflowModel).filter(models.WorkflowModel.id == workflow_id).first()
    if not workflow:
        return None
    workflow.name = name
    workflow.workflow_json = workflow_json
    workflow.description = description
    db.commit()
    db.refresh(workflow)
    return workflow


def delete_workflow(db: Session, workflow_id: int):
    workflow = db.query(models.WorkflowModel).filter(models.WorkflowModel.id == workflow_id).first()
    if not workflow:
        return False
    db.delete(workflow)
    db.commit()
    return True


def set_workflow_enabled(db: Session, workflow_id: int, enabled: bool):
    workflow = db.query(models.WorkflowModel).filter(models.WorkflowModel.id == workflow_id).first()
    if not workflow:
        return None
    workflow.enabled = enabled
    db.commit()
    db.refresh(workflow)
    return workflow
