
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.services import workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/", response_model=Page[schemas.WorkflowSchema])
def get_workflows(db: Session = Depends(get_db), q: str | None = Query(default=None)) -> Page[schemas.WorkflowSchema]:
    return workflow_service.get_workflows(db, q=q)


@router.get("/{workflow_id}", response_model=schemas.WorkflowSchema)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = workflow_service.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("/", response_model=schemas.WorkflowSchema)
def create_workflow(body: schemas.WorkflowCreateBody, db: Session = Depends(get_db)):
    return workflow_service.create_workflow(db, body.name, body.workflow_json, body.description)


@router.put("/{workflow_id}", response_model=schemas.WorkflowSchema)
def update_workflow(workflow_id: int, body: schemas.WorkflowCreateBody, db: Session = Depends(get_db)):
    wf = workflow_service.update_workflow(db, workflow_id, body.name, body.workflow_json, body.description)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.patch("/{workflow_id}/enabled", response_model=schemas.WorkflowSchema)
def set_workflow_enabled(workflow_id: int, enabled: bool = Body(..., embed=True), db: Session = Depends(get_db)):
    wf = workflow_service.set_workflow_enabled(db, workflow_id, enabled)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    ok = workflow_service.delete_workflow(db, workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"ok": True}
