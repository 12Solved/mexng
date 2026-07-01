from email.utils import parseaddr

from .base_step import Step


class ProviderFilterStep(Step):

  """
  Filters emails by sender domain.
  Stops the workflow if the sender's domain does not match the configured provider_domain.
  Sets 'provider' in context with the matched domain on success.
  """

  category = "filtering"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {"provider": "string"}
  config_schema = {
      "provider_domain": {
          "type": "string",
          "required": True,
          "label": "Provider domain",
          "placeholder": "e.g. gmail.com",
      }
  }

  def execute(self, context):
    email = context.get("email")

    if not email.sender:
      context.set("@stop", True)
      return

    address = parseaddr(email.sender)[1]
    domain = address.split("@")[-1].lower()

    provider_domain = self.config["provider_domain"].lower()

    if not domain.endswith(provider_domain):
      context.set("@stop", True)
      return
    self.logger.info(
    "Email provider matches",
    extra={
        "event_type": "PROVIDER_MATCHED",
        "step": self.step_name,
        "email_id": getattr(email, "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id", None),
    })

    context.set("provider", domain)
