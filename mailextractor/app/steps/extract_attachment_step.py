from .base_step import Step


class ExtractAttachmentsStep(Step):

  """
  Extracts all attachments from the email and puts them into context as a list.
  Use this before a foreach step to iterate over attachments.
  """

  category = "extraction"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {"attachments": "Attachment[]"}
  config_schema = {}

  def execute(self, context):
    email = context.get("email")
    self.logger.info(
      f"Attachments extracted for {getattr(email, 'subject', None)}",
      extra={
          "event_type": "EXTRACTED_ATTACHMENT/-S",
          "step": self.step_name,
          "email_id": getattr(email, "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id", None),
      })
    context.set("attachments", email.attachments or [])
