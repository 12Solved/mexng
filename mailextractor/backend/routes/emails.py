import io
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.services import email_service

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/")
def read_emails(db: Session = Depends(get_db), body: schemas.EmailSearchBody = Body(default=schemas.EmailSearchBody())) -> Page[schemas.Email]:
    try:
        return email_service.get_emails(db, body.query, body.workflow_id, body.run_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{email_id}")
def read_email(email_id: int, db: Session = Depends(get_db)):
    result = email_service.get_email(db, email_id)
    if not result:
        raise HTTPException(status_code=404, detail="Email not found")
    return result


@router.get("/{email_id}/attachments/{attachment_id}/download")
def download_attachment(email_id: int, attachment_id: int, db: Session = Depends(get_db)):
    att = email_service.get_attachment(db, attachment_id)
    if not att or att.email_id != email_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if not att.content:
        raise HTTPException(status_code=404, detail="Attachment has no content")
    return StreamingResponse(
        io.BytesIO(bytes(att.content)),
        media_type=att.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(att.filename)}"}
    )


@router.get("/{email_id}/download")
def download_email(email_id: int, db: Session = Depends(get_db)):
    result = email_service.build_email_eml(db, email_id)
    if not result:
        raise HTTPException(status_code=404, detail="Email not found")

    stream, filename = result
    return StreamingResponse(
        stream,
        media_type="message/rfc822",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )
