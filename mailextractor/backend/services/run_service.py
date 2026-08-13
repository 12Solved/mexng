from sqlalchemy.orm import joinedload, Session

from mailextractor import models
from mailextractor.app.workflow import Workflow
from mailextractor.backend import schemas


def _is_run_queued(db: Session, email_id: int, workflow_id: int, run_options: dict) -> bool:
    """Check if a run with the same run_options is already queued."""
    is_dry_run = run_options.get("@dry_run", False)

    queued_runs = db.query(models.WorkflowRun).filter(
        models.WorkflowRun.workflow_id == workflow_id,
        models.WorkflowRun.email_id == email_id,
        models.WorkflowRun.state == models.RunState.re_run,
    ).all()

    for queued_run in queued_runs:
        queued_is_dry = (queued_run.run_options or {}).get("@dry_run", False)
        if queued_is_dry == is_dry_run:
            return True

    return False


def run_all_workflows(db: Session, email_id: int, run_options: dict | None = None):
    run_options = run_options or {}
    is_dry_run = run_options.get("@dry_run", False)

    email = db.query(models.Email).options(joinedload(models.Email.attachments)).filter(models.Email.id == email_id).first()
    if not email:
        return None

    workflows = db.query(models.WorkflowModel).filter(models.WorkflowModel.enabled).all()

    queued_count = 0
    already_queued_count = 0

    for workflow in workflows:
        if _is_run_queued(db, email_id, workflow.id, run_options):
            already_queued_count += 1
            continue

        db.add(models.WorkflowRun(
            workflow_id=workflow.id,
            email_id=email_id,
            state=models.RunState.re_run,
            run_options=run_options or None,
        ))
        queued_count += 1

    db.commit()
    return {"queued": queued_count, "already_queued": already_queued_count}


def test_run_workflow(db: Session, workflow_json: dict, email_id: int, workflow_id: int | None = None):
    email = db.query(models.Email).options(joinedload(models.Email.attachments)).filter(models.Email.id == email_id).first()
    if not email:
        return None

    run_options = {"@dry_run": True}
    run = None
    if workflow_id is not None:
        run = models.WorkflowRun(
            workflow_id=workflow_id,
            email_id=email_id,
            state=models.RunState.running,
            run_options=run_options,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

    try:
        workflow = Workflow(workflow_json, workflow_id=workflow_id, run_id=run.id if run else None)
        context = workflow.run(email, run_options=run_options)
        state = models.RunState.skipped if context.get("@stop") else models.RunState.success
    except Exception:
        state = models.RunState.failed

    if run is not None:
        run.state = state
        db.commit()

    return run.id if run is not None else None, state


def get_runs_by_email(db: Session, email_id: int):
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        return None

    runs = db.query(models.WorkflowRun, models.WorkflowModel.name)\
        .join(models.WorkflowModel, models.WorkflowRun.workflow_id == models.WorkflowModel.id)\
        .filter(models.WorkflowRun.email_id == email_id)\
        .all()

    result = []
    for run, workflow_name in runs:
        schema = schemas.WorkflowRun.model_validate(run)
        schema.workflow_name = workflow_name
        result.append(schema)
    return result


def rerun_workflow_run(db: Session, email_id: int, run_id: int, run_options: dict | None = None):
    run_options = run_options or {}
    is_dry_run = run_options.get("@dry_run", False)

    run = db.query(models.WorkflowRun).filter(
        models.WorkflowRun.id == run_id,
        models.WorkflowRun.email_id == email_id,
    ).first()
    if not run:
        return None, False

    # Check if a run with same options is already queued
    if _is_run_queued(db, email_id, run.workflow_id, run_options):
        # Find and return the queued run that matches the options
        queued_runs = db.query(models.WorkflowRun).filter(
            models.WorkflowRun.workflow_id == run.workflow_id,
            models.WorkflowRun.email_id == email_id,
            models.WorkflowRun.state == models.RunState.re_run,
        ).all()
        
        for queued in queued_runs:
            queued_is_dry = (queued.run_options or {}).get("@dry_run", False)
            if queued_is_dry == is_dry_run:
                return queued, True  # Already queued

    new_run = models.WorkflowRun(
        workflow_id=run.workflow_id,
        email_id=run.email_id,
        state=models.RunState.re_run,
        parent_run_id=run.id,
        run_options=run_options or None,
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    return new_run, False  # Newly queued


def rerun_all_workflow_runs(db: Session, email_id: int, run_options: dict | None = None):
    run_options = run_options or {}

    all_runs = db.query(models.WorkflowRun).filter(
        models.WorkflowRun.email_id == email_id
    ).all()

    latest_by_workflow: dict[int | None, models.WorkflowRun] = {}
    for run in all_runs:
        wf_id = run.workflow_id
        if wf_id not in latest_by_workflow or run.id > latest_by_workflow[wf_id].id:
            latest_by_workflow[wf_id] = run

    queued_count = 0
    already_queued_count = 0

    for run in latest_by_workflow.values():
        if _is_run_queued(db, email_id, run.workflow_id, run_options):
            already_queued_count += 1
            continue

        db.add(models.WorkflowRun(
            workflow_id=run.workflow_id,
            email_id=email_id,
            state=models.RunState.re_run,
            parent_run_id=run.id,
            run_options=run_options or None,
        ))
        queued_count += 1

    db.commit()
    return {"queued": queued_count, "already_queued": already_queued_count}


def run_new_workflows(db: Session, email_id: int, run_options: dict | None = None):
    run_options = run_options or {}

    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        return 0

    already_run_workflow_ids = {
        run.workflow_id for run in db.query(models.WorkflowRun)
        .filter(models.WorkflowRun.email_id == email_id)
        .all()
    }

    new_workflows = db.query(models.WorkflowModel).filter(
        models.WorkflowModel.enabled,
        ~models.WorkflowModel.id.in_(already_run_workflow_ids),
    ).all()

    for workflow in new_workflows:
        db.add(models.WorkflowRun(
            workflow_id=workflow.id,
            email_id=email_id,
            state=models.RunState.re_run,
            run_options=run_options or None,
        ))

    db.commit()
    return len(new_workflows)