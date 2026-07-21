import re

from .base_step import Step


class MatchSubjectStep(Step):

  """
  Filters emails by the subject line using a case-insensitive, dotall regex.
  Stops the workflow if the subject does not match the configured pattern.
  """

  category = "filtering"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {}
  config_schema = {
      "pattern": {
          "type": "string",
          "required": True,
          "label": "Subject pattern",
          "placeholder": "e.g. Invoice #\\d+ or Daily.*Report",
          "description": "Case-insensitive regex, matched anywhere in the subject line.",
      }
  }

  def execute(self, context):
    email = context.get("email")
    subject = email.subject or ""
    pattern = self.config["pattern"]

    if not re.search(pattern, subject, re.IGNORECASE | re.DOTALL):
      context.set("@stop", True)
      return

    self.logger.info(
    "Subject matches",
    extra={
        "event_type": "SUBJECT_MATCHED",
        "step": self.step_name,
        "email_id": getattr(email, "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id", None),
    })
