import os

from .base_step import Step


class ExtractExtensionStep(Step):

  """
  Extracts the file extension from the current attachment's filename.
  Sets 'ext' in context as a lowercase string without the leading dot (e.g. 'pdf', 'xlsx').
  """

  category = "extraction"
  node_type = "default"
  args_in = {"current": "Attachment"}
  args_out = {"ext": "string"}
  config_schema = {}

  def execute(self, context):

    attachment = context.get("current")

    filename = attachment.filename or ""

    _, ext = os.path.splitext(filename)

    ext = ext.lstrip(".").lower()
    self.logger.info(
      f"Extension extracted from {getattr(context.get('attachment'), 'filename', None)}",
      extra={
          "event_type": "EXTRACTED_ATTACHMENT/-S",
          "step": self.step_name,
          "email_id": getattr(context.get("email"), "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id", None),
      })
    context.set("ext", ext)
