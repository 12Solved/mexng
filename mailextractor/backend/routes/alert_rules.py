from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.deps import current_user
from mailextractor.backend.services import alert_rule_service, checkpoint_service, workflow_service
from mailextractor.models import User

router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])


def _require_targets(db: Session, fields: dict):
    workflow_id = fields.get("workflow_id")
    if workflow_id is not None and not workflow_service.get_workflow(db, workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    checkpoint_id = fields.get("checkpoint_id")
    if checkpoint_id is not None and not checkpoint_service.get_checkpoint(db, checkpoint_id):
        raise HTTPException(status_code=404, detail="Checkpoint not found")


def _target_gone() -> HTTPException:
    # The workflow or checkpoint was deleted after _require_targets saw it.
    return HTTPException(status_code=404, detail="Workflow or checkpoint not found")


@router.get("/", response_model=Page[schemas.AlertRuleSchema])
def list_alert_rules(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return alert_rule_service.get_alert_rules(db, user.id)


@router.post("/", response_model=schemas.AlertRuleSchema)
def create_alert_rule(body: schemas.AlertRuleBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    fields = body.model_dump()
    _require_targets(db, fields)
    try:
        return alert_rule_service.create_alert_rule(db, user.id, fields)
    except IntegrityError:
        db.rollback()
        raise _target_gone()


@router.patch("/{rule_id}", response_model=schemas.AlertRuleSchema)
def update_alert_rule(rule_id: int, body: schemas.AlertRuleBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    fields = body.model_dump(exclude_unset=True)
    _require_targets(db, fields)
    try:
        rule = alert_rule_service.update_alert_rule(db, rule_id, user.id, fields)
    except IntegrityError:
        db.rollback()
        raise _target_gone()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.delete("/{rule_id}")
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ok = alert_rule_service.delete_alert_rule(db, rule_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"ok": True}
