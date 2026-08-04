import fnmatch

from .base_step import Step


class AttachmentPatternMapStep(Step):

  """
  Filters the current attachment against an ordered list of filename
  patterns, each paired with a filename template. On the first match, stores
  the matched template in context under 'matched_filename' for a following
  save_attachment_step to consume via filename_template: "${matched_filename}".
  Stops the workflow branch (no save) if no pattern matches, or if the
  matched pattern's template half is left empty (pattern=> with nothing
  after it - matched but explicitly skipped).
  Example: '*_CashPositions.csv=>Cash_${date}.csv;*_SecurityPositions.csv=>Positions_${date}.csv'
  """

  category = "filtering"
  node_type = "default"
  args_in = {"current": "Attachment"}
  args_out = {"matched_filename": "string"}
  config_schema = {
      "pattern_map": {
          "type": "string",
          "required": True,
          "label": "Pattern -> filename template map",
          "placeholder": "*_SecurityPositions.csv=>Position_${date}.csv;*_CashPositions.csv=>Cash_${date}.csv",
          "description": "Semicolon-separated pattern=>filename_template pairs, checked in order; first match wins. Leave the template half empty (pattern=>) to match but skip saving. Pair with a following save_attachment_step using filename_template: \"${matched_filename}\".",
      }
  }

  def execute(self, context):

    attachment = context.get("current")

    filename = attachment.filename or ""

    for pattern, filename_template in self._parse_pattern_map():
      if not fnmatch.fnmatch(filename, pattern):
        continue

      if not filename_template:
        self.logger.info(
        f"Attachment {filename} MATCHES PATTERN '{pattern}' WITH NO TARGET - SKIPPING",
        extra={
            "event_type": "ATTACHMENT_PATTERN_SKIPPED",
            "step": self.step_name,
            "email_id": getattr(context.get("email"), "id", None),
            "workflow_id": context.get("workflow_id"),
            "run_id": context.get("run_id"),
        })
        context.set("@stop", True)
        return

      self.logger.info(
      f"Attachment {filename} MATCHES PATTERN '{pattern}'",
      extra={
          "event_type": "NEEDED_ATTACHMENT_FOUND",
          "step": self.step_name,
          "email_id": getattr(context.get("email"), "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id"),
      })
      context.set("matched_filename", filename_template)
      return

    self.logger.info(
    f"Attachment {filename} DOES NOT MATCH ANY PATTERN",
    extra={
        "event_type": "NEEDED_ATTACHMENT_NOT_FOUND",
        "step": self.step_name,
        "email_id": getattr(context.get("email"), "id", None),
        "workflow_id": context.get("workflow_id"),
        "run_id": context.get("run_id"),
    })
    context.set("@stop", True)

  def _parse_pattern_map(self):
    pairs = []
    for pair in (self.config.get("pattern_map") or "").split(";"):
      pair = pair.strip()
      if not pair:
        continue
      pattern, _, filename_template = pair.partition("=>")
      pairs.append((pattern.strip(), filename_template.strip()))
    return pairs
