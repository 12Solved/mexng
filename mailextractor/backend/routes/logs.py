from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.services import log_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/")
def read_logs(
    db: Session = Depends(get_db),
    event_type: str | None = Query(None),
    workflow_id: str | None = Query(None),
    email_id: str | None = Query(None),
    run_id: str | None = Query(None),
    attachment_id: str | None = Query(None),
    level: str | None = Query(None),
    run_state: str | None = Query(None, description="Filter by run state: success, failed, running, skipped, re_run"),
    q: str | None = Query(
        None,
        description=(
            'Space-separated tags and text. Tags: workflow:N email:N run:N attachment:N '
            'event:substring step:substring. Other tokens search message/step (ILIKE, AND).'
        ),
    ),
) -> Page[schemas.Log]:
    return log_service.get_logs(
        db,
        event_type=event_type,
        email_id=email_id,
        workflow_id=workflow_id,
        run_id=run_id,
        attachment_id=attachment_id,
        level=level,
        run_state=run_state,
        q=q,
    )


@router.get("/filters")
def log_filters(db: Session = Depends(get_db)):
    return log_service.get_log_filters(db)
