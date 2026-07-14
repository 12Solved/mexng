import re
from email.utils import getaddresses

from .base_step import Step

RECIPIENT_HEADERS = ("To", "Cc", "Bcc", "X-Original-To")
ANY_HEADER_OPTION = "Any (To, Cc, Bcc, X-Original-To)"


class MatchRecipientAddressStep(Step):

  """
  Filters emails by a recipient address using a case-insensitive regex.
  Checks a single header (To/Cc/Bcc/X-Original-To) or, with the 'Any' option,
  matches if the pattern matches an address in any of them.
  Stops the workflow if no candidate address matches.
  Sets 'recipient_address' in context with the first matched address on success.
  """

  category = "filtering"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {"recipient_address": "string"}
  config_schema = {
      "header": {
          "type": "string",
          "required": False,
          "label": "Header to match",
          "default": "To",
          "options": [*RECIPIENT_HEADERS, ANY_HEADER_OPTION],
          "description": "Which recipient header to check. 'Any' matches if the pattern matches an address in any of To/Cc/Bcc/X-Original-To.",
      },
      "pattern": {
          "type": "string",
          "required": True,
          "label": "Recipient address pattern",
          "placeholder": "e.g. bank.*@ or .*@example\\.com$",
          "description": "Case-insensitive regex, matched anywhere in each candidate recipient address.",
      },
  }

  def execute(self, context):
    email = context.get("email")
    header = self.config.get("header") or "To"
    pattern = self.config["pattern"]

    headers_to_check = RECIPIENT_HEADERS if header == ANY_HEADER_OPTION else [header]

    candidates = []
    for name in headers_to_check:
      raw_value = self._header_value(name, email)
      if raw_value:
        candidates.extend(addr for _, addr in getaddresses([raw_value]) if addr)

    match = next((addr for addr in candidates if re.search(pattern, addr, re.IGNORECASE)), None)

    if match is None:
      context.set("@stop", True)
      return

    self.logger.info(
    "Recipient address matches",
    extra={
        "event_type": "RECIPIENT_MATCHED",
        "step": self.step_name,
        "email_id": getattr(email, "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id", None),
    })

    context.set("recipient_address", match)

  def _header_value(self, name, email):
    if name.lower() == "to" and getattr(email, "recipient", None):
      return email.recipient

    raw_headers = getattr(email, "raw_headers", None) or {}
    for key, value in raw_headers.items():
      if key.lower() == name.lower():
        return value
    return None
