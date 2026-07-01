import os
import sys

from sqlalchemy import create_engine, exists
from sqlalchemy.orm import joinedload, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.app.config import config
from mailextractor.app.workflow import Workflow
from mailextractor.models import Email, RunState, WorkflowModel, WorkflowRun

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

logger = setup_logging(engine)


workflow_rows = session.query(WorkflowModel)\
    .filter(WorkflowModel.enabled)\
    .all()

workflows = []

for w in workflow_rows:
    try:
        workflows.append((Workflow(w.workflow_json, workflow_id=w.id), w.id))
    except Exception:
        logger.exception(
            "Failed to initialize workflow",
            extra={
                "event_type": "WORKFLOW_INIT_FAILED",
                "workflow_id": getattr(w, "id", None)
            }
        )

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

if not emails_to_process:
    print("Nothing to process.")
else:
    for email in emails_to_process:
        logger.info(
            f"Starting process for {email.subject}",
            extra={
                "event_type": "EMAIL_PROCESSING_STARTED",
                "step": "ProcessRunner",
                "email_id": email.id,
            }
        )

        re_run_workflow_ids = {
            run.workflow_id for run in session.query(WorkflowRun)
            .filter_by(email_id=email.id, state=RunState.re_run)
            .all()
        }
        is_fresh = len(re_run_workflow_ids) == 0

        any_success = False

        for workflow, workflow_id in workflows:
            if not is_fresh and workflow_id not in re_run_workflow_ids:
                continue

            run = session.query(WorkflowRun).filter_by(
                workflow_id=workflow_id, email_id=email.id, state=RunState.re_run).first()

            if run:
                run.state = RunState.running
            else:
                run = WorkflowRun(workflow_id=workflow_id, email_id=email.id, state=RunState.running)
                session.add(run)

            session.commit()
            workflow.run_id = run.id

            # Extract run options (defaults to empty dict if None)
            run_options = run.run_options or {}

            try:
                # Pass options to workflow.run - they'll be merged into context
                context = workflow.run(email, run_options=run_options)

                if context.get("@stop"):
                    run_state = RunState.skipped
                else:
                    run_state = RunState.success
                    any_success = True

            except Exception:
                logger.exception(
                    "Workflow execution failed",
                    extra={
                        "event_type": "WORKFLOW_FAILED",
                        "email_id": email.id,
                        "workflow_id": workflow_id,
                        "run_id": run.id,
                    }
                )
                run_state = RunState.failed

            run.state = run_state
            session.commit()

        logger.info(
            f"Finished process for {email.subject}",
            extra={
                "event_type": "EMAIL_PROCESSING_FINISHED",
                "step": "ProcessRunner",
                "email_id": email.id
            }
        )

    print(f"{len(emails_to_process)} email(s) processed.")

session.close()
