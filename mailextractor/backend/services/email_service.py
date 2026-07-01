import email.mime.base as mime_base
import email.mime.multipart as mime_multipart
import email.mime.text as mime_text
import io
from email import encoders
from urllib.parse import quote

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from mailextractor import models
from mailextractor.backend import schemas
from mailextractor.backend.utils.query_filter import build_filter


def get_emails(db: Session, filter_query: dict | None = None, workflow_id: int | None = None, run_state: str | None = None):
    query = select(models.Email).order_by(models.Email.created_at.desc())

    if workflow_id is not None or run_state is not None:
        run_subquery = select(models.WorkflowRun.email_id)
        if workflow_id is not None:
            run_subquery = run_subquery.where(models.WorkflowRun.workflow_id == workflow_id)
        if run_state is not None:
            run_subquery = run_subquery.where(models.WorkflowRun.state == models.RunState(run_state))
        query = query.where(models.Email.id.in_(run_subquery))

    if filter_query and filter_query.get("rules"):
        query = query.where(build_filter(models.Email, filter_query))

    emails = paginate(db, query)
    result = []
    for email in emails.items:
        runs = db.query(models.WorkflowRun).filter(models.WorkflowRun.email_id == email.id).all()
        latest_by_workflow: dict = {}
        for r in runs:
            # Skip dry-runs when determining latest production state
            is_dry_run = (r.run_options or {}).get("@dry_run", False)
            if is_dry_run:
                continue
            
            wf_id = r.workflow_id
            if wf_id not in latest_by_workflow or r.id > latest_by_workflow[wf_id].id:
                latest_by_workflow[wf_id] = r
        latest_runs = list(latest_by_workflow.values())
        summary = schemas.WorkflowRunSummary(
            success=sum(1 for r in latest_runs if r.state == models.RunState.success),
            failed=sum(1 for r in latest_runs if r.state == models.RunState.failed),
            skipped=sum(1 for r in latest_runs if r.state == models.RunState.skipped),
            re_run=sum(1 for r in latest_runs if r.state == models.RunState.re_run)
        )
        email_schema = schemas.Email.model_validate(email)
        email_schema.run_summary = summary
        result.append(email_schema)
    emails.items = result
    return emails


def get_email(db: Session, email_id: int):
    email = db.query(models.Email)\
        .options(joinedload(models.Email.attachments))\
        .filter(models.Email.id == email_id)\
        .first()
    if not email:
        return None

    runs = db.query(models.WorkflowRun)\
        .filter(models.WorkflowRun.email_id == email_id)\
        .all()

    latest_by_workflow: dict = {}
    for r in runs:
        # Skip dry-runs when determining latest production state
        is_dry_run = (r.run_options or {}).get("@dry_run", False)
        if is_dry_run:
            continue
        
        wf_id = r.workflow_id
        if wf_id not in latest_by_workflow or r.id > latest_by_workflow[wf_id].id:
            latest_by_workflow[wf_id] = r
    latest_runs = list(latest_by_workflow.values())

    email_schema = schemas.Email.model_validate(email)
    email_schema.run_summary = schemas.WorkflowRunSummary(
        success=sum(1 for r in latest_runs if r.state == models.RunState.success),
        failed=sum(1 for r in latest_runs if r.state == models.RunState.failed),
        skipped=sum(1 for r in latest_runs if r.state == models.RunState.skipped),
        re_run=sum(1 for r in latest_runs if r.state == models.RunState.re_run),
    )
    return email_schema


def get_attachment(db: Session, attachment_id: int):
    return db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()


def build_email_eml(db: Session, email_id: int) -> tuple[io.BytesIO, str] | None:
    email_record = db.query(models.Email)\
        .options(joinedload(models.Email.attachments))\
        .filter(models.Email.id == email_id)\
        .first()
    if not email_record:
        return None

    msg = mime_multipart.MIMEMultipart()

    for key, value in (email_record.raw_headers or {}).items():
        if key.lower() not in ("content-type", "mime-version"):
            msg[key] = value

    msg.attach(mime_text.MIMEText(email_record.body or "", "plain", "utf-8"))
    if email_record.html_body:
        msg.attach(mime_text.MIMEText(email_record.html_body, "html", "utf-8"))

    for att in email_record.attachments:
        if not att.content:
            continue
        part = mime_base.MIMEBase(*((att.content_type or "application/octet-stream").split("/", 1)))
        part.set_payload(bytes(att.content))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=att.filename)
        msg.attach(part)

    filename = quote(email_record.subject or "email") + ".eml"
    return io.BytesIO(msg.as_bytes()), filename
