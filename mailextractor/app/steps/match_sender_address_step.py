import re
from email.utils import parseaddr

from .base_step import Step


class MatchSenderAddressStep(Step):

  """
  Filters emails by the sender's address using a case-insensitive regex.
  Stops the workflow if the sender's address does not match the configured pattern.
  Sets 'sender_address' in context with the matched address on success.
  """

  category = "filtering"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {"sender_address": "string"}
  config_schema = {
      "pattern": {
          "type": "string",
          "required": True,
          "label": "Sender address pattern",
          "placeholder": "e.g. .*@gmail\\.com$ or light@bank\\.com",
          "description": "Case-insensitive regex, matched anywhere in the sender's email address.",
      }
  }

  def execute(self, context):
    email = context.get("email")

    if not email.sender:
      context.set("@stop", True)
      return

    address = parseaddr(email.sender)[1]
    pattern = self.config["pattern"]

    if not re.search(pattern, address, re.IGNORECASE):
      context.set("@stop", True)
      return

    self.logger.info(
    "Sender address matches",
    extra={
        "event_type": "SENDER_MATCHED",
        "step": self.step_name,
        "email_id": getattr(email, "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id", None),
    })

    context.set("sender_address", address)
