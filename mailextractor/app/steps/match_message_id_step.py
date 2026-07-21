import re

from .base_step import Step


class MatchMessageIdStep(Step):

  """
  Filters emails by the Message-ID header using a case-insensitive regex.
  Stops the workflow if the Message-ID does not match the configured pattern.
  """

  category = "filtering"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {}
  config_schema = {
      "pattern": {
          "type": "string",
          "required": True,
          "label": "Message-ID pattern",
          "placeholder": "e.g. @reports\\.example\\.com>$",
          "description": "Case-insensitive regex, matched anywhere in the Message-ID header (including the surrounding <>).",
      }
  }

  def execute(self, context):
    email = context.get("email")
    message_id = email.message_id or ""
    pattern = self.config["pattern"]

    if not re.search(pattern, message_id, re.IGNORECASE):
      context.set("@stop", True)
      return

    self.logger.info(
    "Message-ID matches",
    extra={
        "event_type": "MESSAGE_ID_MATCHED",
        "step": self.step_name,
        "email_id": getattr(email, "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id", None),
    })
