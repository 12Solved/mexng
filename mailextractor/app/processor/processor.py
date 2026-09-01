import os
import sys

from sqlalchemy import create_engine, exists
from sqlalchemy.orm import joinedload, sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config
from mailextractor.app.workflow import Workflow
from mailextractor.models import Email, RunState, WorkflowModel, WorkflowRun
from mailextractor.app.config import config

def get_workflows_from_db(session, logger = None):
    workflow_rows = session.query(WorkflowModel).filter(WorkflowModel.enabled).all()
    workflows = []
    for w in workflow_rows:
        try:
            workflows.append(Workflow(w.workflow_json, workflow_id=w.id))
        except Exception:
            if logger: logger.exception("Failed to initialize workflow", extra={"event_type": "WORKFLOW_INIT_FAILED", "workflow_id": getattr(w, "id", None)})
    return workflows

def get_emails_from_db(session, logger = None):
    emails_to_process = session.query(Email)\
        .options(joinedload(Email.attachments))\
        .filter(
            ~exists().where(WorkflowRun.email_id == Email.id) |
            exists().where(
                (WorkflowRun.email_id == Email.id) &
                (WorkflowRun.state == RunState.re_run)
            )
        )\
        .order_by(Email.date.desc())\
        .all()
    return emails_to_process

def get_re_run_workflow_ids_from_db(session, emails, logger = None):
    res = {}
    for e in emails:
        e_id = e.id
        r_ids = {
            run.workflow_id for run in session.query(WorkflowRun)
            .filter_by(email_id=e_id, state=RunState.re_run)
            .all()
        }
        if (len(r_ids) > 0):
            res[e_id] = r_ids
    return res   

def get_run_groups(emails, workflows, re_run_workflow_ids={}, logger=None):
    for email in emails:
        re_run_ids = re_run_workflow_ids.get(email.id, None)
        if re_run_ids is None:
            email_workflows = workflows
        else:
            email_workflows = [w for w in workflows if w.workflow_id in re_run_ids]
        yield email, email_workflows

def run_dry(groups, logger=None):
    for e, workflows in groups:
        for w in workflows:
            res = w.run(e, run_options={})
    return None

def run_db(session, groups, logger=None):
    for e, workflows in groups:
        e_id = e.id
        if logger: logger.info(f"Starting process for {e.subject}", extra={"event_type": "EMAIL_PROCESSING_STARTED", "step": "ProcessRunner", "email_id": e_id,})

        for w in workflows:
            w_id = w.workflow_id
            run = session.query(WorkflowRun).filter_by(workflow_id=w_id, email_id=e_id, state=RunState.re_run).first()
            if run:
                run.state = RunState.running
            else:
                run = WorkflowRun(workflow_id=w_id, email_id=e_id, state=RunState.running)
                session.add(run)
            session.commit()
            w.run_id = run.id
            run_options = run.run_options or {}
            try:
                # Pass options to workflow.run - they'll be merged into context
                context = w.run(e, run_options=run_options)
                if context.get("@stop"):
                    run_state = RunState.skipped
                else:
                    run_state = RunState.success
            except Exception:
                if logger: logger.exception("Workflow execution failed", extra={"event_type": "WORKFLOW_FAILED", "email_id": e_id, "workflow_id": w_id, "run_id": run.id,})
                run_state = RunState.failed

            run.state = run_state
            session.commit()

        if logger: logger.info(f"Finished process for {e.subject}", extra={"event_type": "EMAIL_PROCESSING_FINISHED", "step": "ProcessRunner", "email_id": e_id})
    return None

def process(config):
    engine = create_engine(config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    logger = setup_logging(engine)
    session = Session()

    workflows = get_workflows_from_db(session, logger=logger)
    emails = get_emails_from_db(session, logger=logger)
    re_run_workflow_ids = get_re_run_workflow_ids_from_db(session, emails, logger=logger)
    groups = get_run_groups(emails, workflows, re_run_workflow_ids, logger=logger)
    run_db(session, groups, logger)

    session.close()
    return None

def main():
    process(config)

if __name__ == "__main__":
    main()
