import fnmatch
import json

from .base_step import Step


class AttachmentPatternMapStep(Step):

  """
  Filters the current attachment against an ordered list of filename
  patterns, each paired with a filename template. On the first match, stores
  the matched template in context under 'matched_filename' for a following
  save_attachment_step to consume via filename_template: "${matched_filename}".
  Stops the workflow branch (no save) if no pattern matches, or if the
  matched pattern's template half is left empty (pattern with an empty
  template - matched but explicitly skipped).
  Example: '[{"pattern": "*_CashPositions.csv", "template": "Cash_${date}.csv"}, {"pattern": "*_SecurityPositions.csv", "template": "Positions_${date}.csv"}]'
  """

  category = "filtering"
  node_type = "default"
  args_in = {"current": "Attachment"}
  args_out = {"matched_filename": "string"}
  config_schema = {
      "pattern_map": {
          "type": "json_list",
          "required": True,
          "label": "Pattern -> filename template map",
          "placeholder": '[{"pattern":"*_SecurityPositions.csv","template":"Position_${date}.csv"},{"pattern":"*_CashPositions.csv","template":"Cash_${date}.csv"}]',
          "description": "Ordered list of {pattern, template} pairs, checked in order; first match wins. Leave the template empty to match but skip saving. Pair with a following save_attachment_step using filename_template: \"${matched_filename}\". Stored as a JSON array of objects.",
          "columns": [
              {"key": "pattern", "label": "Pattern", "placeholder": "*_A.csv"},
              {"key": "template", "label": "Filename template", "placeholder": "A_${date}.csv"},
          ],
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
    pattern_map_raw = self.config.get("pattern_map") or "[]"
    try:
      entries = json.loads(pattern_map_raw)
    except json.JSONDecodeError as exc:
      raise ValueError(f"AttachmentPatternMapStep: 'pattern_map' must be a JSON array of {{pattern, template}} objects, got {pattern_map_raw!r}.") from exc

    return [(entry.get("pattern", "").strip(), entry.get("template", "").strip()) for entry in entries]
