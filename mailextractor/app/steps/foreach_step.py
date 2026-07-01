import os

from .base_step import Step


class ForEachStep(Step):

  """
  Iterates over a list from context and runs a sub-workflow for each item.
  Each item is available inside the loop under the reserved context key 'current'.
  The 'stop' flag is reset between iterations so inner filter steps
  don't bleed through to the next item.
  """

  category = "control"
  node_type = "container"
  args_in = {"collection": "any[]"}
  args_out = {}
  config_schema = {
      "collection": {
        "type": "string",
        "required": True,
        "label": "Collection variable",
        "placeholder": "e.g. attachments",
      },
  }

  def __init__(self, **config):
    super().__init__(**config)

    from mailextractor.app.workflow import Workflow

    self.sub_workflow = Workflow({
      "steps": self.config["steps"]
    })

  def execute(self, context):

    items = context.get(self.config["collection"])

    if not items:
      return

    for item in items:
      attachment_name = getattr(item, "filename", None)
      context.set("current", item)
      context.set("@stop", False)
      name, ext = os.path.splitext(getattr(item, "filename", "") or "")
      context.set("attachment_name", name)
      context.set("ext", ext)
      context.set("content_type", getattr(item, "content_type", None))
      context.set("attachment_size", getattr(item, "size", None))
      self.logger.info(
      f"Running sub-workflow for {attachment_name}",
      extra={
        "event_type": "SUB_WORKFLOW_STARTED",
        "step": self.step_name,
        "email_id": getattr(context.get("email"), "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id", None),
      })
      self.sub_workflow.run_with_context(context)
    context.set("@stop", False)
