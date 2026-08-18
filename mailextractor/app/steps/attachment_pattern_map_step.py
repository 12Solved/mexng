import fnmatch
import json

import mailextractor.app.steputils as stp

from .base_step import Step


class AttachmentPatternMapStep(Step):

  """
  Filters the current attachment against an ordered list of filename
  patterns, each paired with a filename template. Every pattern that matches
  contributes one renamed copy of the attachment (same content, filename
  resolved from that pattern's template) to 'output_var', for a following
  foreach + save_attachment_step to iterate and save. A pattern with an
  empty template matches but is skipped (no copy produced). 'output_var' is
  set to an empty list if no pattern matches, and the branch continues
  rather than stopping.
  Example: '[{"pattern": "*_CashPositions.csv", "template": "Cash_${date}.csv"}, {"pattern": "*_SecurityPositions.csv", "template": "Positions_${date}.csv"}]'
  """

  category = "filtering"
  node_type = "default"
  args_in = {"current": "Attachment"}
  args_out = {"matched_attachments": "Attachment[]"}
  config_schema = {
      "pattern_map": {
          "type": "json_list",
          "required": True,
          "label": "Pattern -> filename template map",
          "placeholder": '[{"pattern":"*_SecurityPositions.csv","template":"Position_${date}.csv"},{"pattern":"*_CashPositions.csv","template":"Cash_${date}.csv"}]',
          "description": "Ordered list of {pattern, template} pairs. Every pattern that matches produces one renamed copy of the attachment. Leave a template empty to match but skip that copy. Pair with a following foreach over 'output_var' + save_attachment_step (unmodified - it saves 'current' using filename_template: \"${attachment_name}\" by default). Stored as a JSON array of objects.",
          "columns": [
              {"key": "pattern", "label": "Pattern", "placeholder": "*_A.csv"},
              {"key": "template", "label": "Filename template", "placeholder": "A_${date}.csv"},
          ],
      },
      "output_var": {
          "type": "string",
          "required": False,
          "label": "Output variable name",
          "default": "matched_attachments",
          "placeholder": "matched_attachments",
          "description": "Context key the matched-copy list is stored under, usable in a nested foreach.",
      },
  }

  def execute(self, context):

    attachment = context.get("current")

    filename = attachment.filename or ""

    output_var = self.config.get("output_var") or "matched_attachments"

    matches = []
    any_pattern_matched = False

    for pattern, filename_template in self._parse_pattern_map():
      if not fnmatch.fnmatch(filename, pattern):
        continue

      any_pattern_matched = True

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
        continue

      self.logger.info(
      f"Attachment {filename} MATCHES PATTERN '{pattern}'",
      extra={
          "event_type": "NEEDED_ATTACHMENT_FOUND",
          "step": self.step_name,
          "email_id": getattr(context.get("email"), "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id"),
      })
      matches.append(stp.ExtractedAttachment(filename_template, attachment.content))

    if not any_pattern_matched:
      self.logger.info(
      f"Attachment {filename} DOES NOT MATCH ANY PATTERN",
      extra={
          "event_type": "NEEDED_ATTACHMENT_NOT_FOUND",
          "step": self.step_name,
          "email_id": getattr(context.get("email"), "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id"),
      })

    context.set(output_var, matches)

  def _parse_pattern_map(self):
    pattern_map_raw = self.config.get("pattern_map") or "[]"
    try:
      entries = json.loads(pattern_map_raw)
    except json.JSONDecodeError as exc:
      raise ValueError(f"AttachmentPatternMapStep: 'pattern_map' must be a JSON array of {{pattern, template}} objects, got {pattern_map_raw!r}.") from exc

    return [(entry.get("pattern", "").strip(), entry.get("template", "").strip()) for entry in entries]
