import fnmatch

from .base_step import Step


class AttachmentPatternStep(Step):

  """
  Filters the current attachment by filename pattern using Unix-style wildcards.
  Stops the workflow branch if the attachment filename does not match the pattern.
  Example patterns: '*.pdf', 'invoice_*.xlsx', 'report-??-2024.csv'
  """

  category = "filtering"
  node_type = "default"
  args_in = {"current": "Attachment"}
  args_out = {}
  config_schema = {
      "pattern": {
          "type": "string",
          "required": True,
          "label": "Filename pattern",
          "placeholder": "e.g. *.pdf or invoice_*.xlsx",
      }
  }

  def execute(self, context):

    attachment = context.get("current")

    filename = attachment.filename or ""

    pattern = self.config["pattern"]

    if not fnmatch.fnmatch(filename, pattern):
      self.logger.info(
      f"Attachment {getattr(attachment, 'filename', None)} DOES NOT MATCH PATTERN",
      extra={
          "event_type": "NEEDED_ATTACHMENT_NOT_FOUND",
          "step": self.step_name,
          "email_id": getattr(context.get("email"), "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id"),
      })
      context.set("@stop", True)
      return

    self.logger.info(
    f"Attachment {getattr(attachment, 'filename', None)} MATCHES PATTERN",
    extra={
        "event_type": "NEEDED_ATTACHMENT_FOUND",
        "step": self.step_name,
        "email_id": getattr(context.get("email"), "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id"),
    })
