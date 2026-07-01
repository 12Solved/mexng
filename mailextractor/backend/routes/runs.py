from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.services import run_service

router = APIRouter(prefix="/emails/{email_id}/runs", tags=["runs"])


@router.get("/", response_model=list[schemas.WorkflowRun])
def get_email_runs(email_id: int, db: Session = Depends(get_db)):
    runs = run_service.get_runs_by_email(db, email_id)
    if runs is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return runs


@router.post("/{run_id}/rerun", response_model=schemas.RerunResponse)
def rerun_workflow_run(
    email_id: int,
    run_id: int,
    body: schemas.RunOptions | None = None,
    db: Session = Depends(get_db),
):
    result, already_queued = run_service.rerun_workflow_run(db, email_id, run_id, run_options=body and body.run_options)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {"run": result, "already_queued": already_queued}


@router.post("/rerun-all")
def rerun_all_workflow_runs(
    email_id: int,
    body: schemas.RunOptions | None = None,
    db: Session = Depends(get_db),
):
    runs = run_service.get_runs_by_email(db, email_id)
    if runs is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return run_service.rerun_all_workflow_runs(db, email_id, run_options=body and body.run_options)


@router.post("/run-all-workflows")
def run_all_workflows(
    email_id: int,
    body: schemas.RunOptions | None = None,
    db: Session = Depends(get_db),
):
    result = run_service.run_all_workflows(db, email_id, run_options=body and body.run_options)
    if result is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return result


@router.post("/run-new-workflows")
def run_new_workflows(
    email_id: int,
    body: schemas.RunOptions | None = None,
    db: Session = Depends(get_db),
):
    count = run_service.run_new_workflows(db, email_id, run_options=body and body.run_options)
    if count == 0:
        return {"queued": 0, "message": "No new workflows to run."}
    return {"queued": count, "message": f"{count} workflow(s) queued."}