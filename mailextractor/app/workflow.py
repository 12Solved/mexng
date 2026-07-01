import logging
from datetime import datetime

from mailextractor.app.resolver import Resolver
from mailextractor.app.steps.STEP_REGISTRY import STEP_REGISTRY
from mailextractor.app.workflow_context import WorkflowContext


class Workflow:

  def __init__(self, workflow_json, workflow_id=None, run_id=None):
    self.steps = self._build_steps(workflow_json)
    self.workflow_json = workflow_json
    self.workflow_id = workflow_id
    self.run_id = run_id
    self.resolver = Resolver()

  def _build_steps(self, workflow_json):
    logger = logging.getLogger(__name__)
    steps = []
    if "steps" not in workflow_json:
      logger.error(
          "Workflow missing 'steps'",
          extra={
              "event_type": "INVALID_WORKFLOW_STRUCTURE",
              "workflow_json": workflow_json
          }
      )
      raise ValueError("Workflow JSON missing 'steps'")
    for step_data in workflow_json["steps"]:
      step_type = step_data["type"]
      if step_type not in STEP_REGISTRY:
        logger.error(
        f"Unknown step type: {step_type}",
        extra={
          "event_type": "INVALID_STEP_TYPE",
          "step": step_type
        })
        raise Exception(f"Unknown step type: {step_type}")

      step_class = STEP_REGISTRY[step_type]

      config = dict(step_data.get("config", {}))

      if "over" in step_data:
        config["collection"] = step_data["over"]
      if "steps" in step_data:
        config["steps"] = step_data["steps"]

      steps.append({
        "class": step_class,
        "config": config
      })

    return steps


  def run(self, email, run_options=None):
    logger = logging.getLogger(__name__)

    run_options = run_options or {}

    logger.info(
    "Workflow started",
      extra={
        "event_type": "WORKFLOW_STARTED",
        "email_id": getattr(email, "id", None),
        "workflow_id": self.workflow_id,
        "run_id": self.run_id,
      }
    )

    context = WorkflowContext({
    "email": email,
    "workflow_id": self.workflow_id,
    "run_id": self.run_id,
    "email_id": email.id,
    "email_subject": email.subject,
    "email_sender": email.sender,
    "email_recipient": email.recipient,
    "date": datetime.now().strftime("%Y%m%d"),
    "timestamp": datetime.now().isoformat(),
    })

    # Merge custom run options into context
    context.data.update(run_options)

    try:
      self.run_with_context(context)

    except Exception:
      logger.exception(
        "Workflow failed internally",
        extra={
          "event_type": "WORKFLOW_FAILED",
          "email_id": getattr(email, "id", None),
          "workflow_id": self.workflow_id,
          "run_id": self.run_id,
        }
      )
      raise
    finally:
      logger.info(
        "Workflow finished",
        extra={
          "event_type": "WORKFLOW_FINISHED",
          "email_id": getattr(email, "id", None),
          "workflow_id": self.workflow_id,
          "run_id": self.run_id,
        }
      )
    return context

  def run_with_context(self, context):
    logger = logging.getLogger(__name__)
    email = context.get("email")
    for step_data in self.steps:

      if context.get("@stop"):
        logger.info(
        "Workflow stopped early",
        extra={"event_type": "WORKFLOW_STOPPED",
               "email_id": getattr(email, "id", None),
               "workflow_id": self.workflow_id,
               "run_id": self.run_id,})
        break

      step_class = step_data["class"]
      raw_config = step_data["config"]

      resolved_config = self.resolver.resolve_config(
        raw_config,
        context.data
      )
      step_instance = step_class(**resolved_config)

      step_instance.run(context)
