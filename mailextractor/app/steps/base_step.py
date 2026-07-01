import logging

from mailextractor.app.steps.STEP_CATEGORIES import STEP_CATEGORIES


class Step:
  args_in = {}
  args_out = []
  category = "general"
  node_type = "default"
  config_schema = {}

  def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    if cls.category not in STEP_CATEGORIES:
      logging.getLogger(cls.__name__).error(f"{cls.__name__}: category '{cls.category}' is not in STEP_CATEGORIES")
      raise ValueError(f"{cls.__name__}: category '{cls.category}' is not in STEP_CATEGORIES")


  def __init__(self, **config):
    self.config = config
    self.logger = logging.getLogger(self.__class__.__name__)
    self.step_name = self.__class__.__name__

  def execute(self, context):
    raise NotImplementedError()

  def run(self, context):
    email = context.get("email", None)
    workflow_id = context.get("workflow_id", None)
    email_id = getattr(email, "id", None) if email else None
    run_id = context.get("run_id", None)
    self.logger.debug(
      f"{self.step_name} started",
      extra={
        "event_type": "STEP_STARTED",
        "step": self.step_name,
        "email_id": email_id,
        "workflow_id": workflow_id,
        "run_id": run_id,
      }
    )

    try:
      self.execute(context)
    except Exception as e:
      self.logger.error(
        f"{self.step_name} crashed: {str(e)}",
        extra={
          "event_type": "STEP_CRASHED",
          "step": self.step_name,
          "email_id": email_id,
          "workflow_id": workflow_id,
          "run_id": run_id,
        }
      )
      raise

    self.logger.debug(
      f"{self.step_name} finished",
      extra={
        "event_type": "STEP_FINISHED",
        "step": self.step_name,
        "email_id": email_id,
        "workflow_id": workflow_id,
        "run_id": run_id,
      }
    )
