import fnmatch
import os
import subprocess
import tempfile

import mailextractor.app.steputils as stp

from .base_step import Step


class ExtractArchiveStep(Step):

  """
  If the current attachment matches an archive pattern (default '*.zip'),
  extracts its members via the `7z` CLI — trying no password, then each
  configured password in order — into 'output_var' for a nested foreach to
  iterate, recursing into nested archives up to 'max_depth'. Otherwise, or if
  every password fails, 'output_var' is set to an empty list and the branch
  continues rather than stopping.
  """

  category = "extraction"
  node_type = "default"
  args_in = {"current": "Attachment"}
  args_out = {"extracted_attachments": "Attachment[]"}
  config_schema = {
      "archive_pattern": {
          "type": "string",
          "required": False,
          "label": "Archive filename pattern",
          "default": "*.zip",
          "placeholder": "*.zip",
          "description": "Unix-style wildcard used to decide whether the current attachment is an archive.",
      },
      "passwords": {
          "type": "string",
          "required": False,
          "label": "Passwords (comma-separated)",
          "placeholder": "secret1,secret2",
          "description": "Tried in order after an unencrypted attempt. Leave blank for unencrypted archives only.",
      },
      "output_var": {
          "type": "string",
          "required": False,
          "label": "Output variable name",
          "default": "extracted_attachments",
          "placeholder": "extracted_attachments",
          "description": "Context key the extracted member list is stored under, usable in a nested foreach.",
      },
      "max_depth": {
          "type": "string",
          "required": False,
          "label": "Max nested archive depth",
          "default": "5",
          "placeholder": "5",
          "description": "Caps recursion into archives found inside archives.",
      },
      "max_seconds": {
          "type": "string",
          "required": False,
          "label": "Extraction timeout (seconds)",
          "default": "60",
          "placeholder": "60",
          "description": "Aborts a single archive's extraction attempt if '7z' runs longer than this.",
      },
  }

  def execute(self, context):
    attachment = context.get("current")
    email = context.get("email")
    archive_pattern = self.config.get("archive_pattern") or "*.zip"
    output_var = self.config.get("output_var") or "extracted_attachments"

    try:
      max_depth = int(self.config.get("max_depth") or 5)
    except (TypeError, ValueError) as exc:
      raise ValueError(f"ExtractArchiveStep: 'max_depth' must be an integer, got {self.config.get('max_depth')!r}.") from exc

    try:
      max_seconds = int(self.config.get("max_seconds") or 60)
    except (TypeError, ValueError) as exc:
      raise ValueError(f"ExtractArchiveStep: 'max_seconds' must be an integer, got {self.config.get('max_seconds')!r}.") from exc

    filename = getattr(attachment, "filename", None) or ""
    if not fnmatch.fnmatch(filename, archive_pattern):
      context.set(output_var, [])
      return

    passwords = [p.strip() for p in (self.config.get("passwords") or "").split(",") if p.strip()]

    extracted = self._extract(
        attachment.content, filename, passwords, max_depth, max_seconds, archive_pattern, context, email,
    )

    self.logger.info(
        f"Extracted {len(extracted)} file(s) from archive '{filename}'",
        extra={
            "event_type": "ARCHIVE_EXTRACTED",
            "step": self.step_name,
            "email_id": getattr(email, "id", None),
            "workflow_id": context.get("workflow_id"),
            "run_id": context.get("run_id"),
        },
    )

    context.set(output_var, extracted)

  def _extract(self, content, archive_name, passwords, depth_remaining, max_seconds, archive_pattern, context, email):
    members = self._open_and_read_members(content, archive_name, passwords, max_seconds, context, email)

    extracted = []
    for member_name, member_content in members:
      extracted.append(stp.ExtractedAttachment(member_name, member_content))

      if depth_remaining > 0 and fnmatch.fnmatch(member_name, archive_pattern):
        extracted.extend(
            self._extract(
                member_content, member_name, passwords, depth_remaining - 1, max_seconds, archive_pattern, context, email,
            )
        )

    return extracted

  def _open_and_read_members(self, content, archive_name, passwords, max_seconds, context, email):
    attempts = [None] + passwords
    last_error = None

    with tempfile.TemporaryDirectory() as tmp_dir:
      archive_path = os.path.join(tmp_dir, "archive")
      with open(archive_path, "wb") as f:
        f.write(content)

      extract_dir = os.path.join(tmp_dir, "extracted")
      os.makedirs(extract_dir, exist_ok=True)

      for password in attempts:
        # '7z e' extracts flat (no member paths), matching today's
        # basename-only ExtractedAttachment naming.
        command = ["7z", "e", "-y", archive_path, f"-o{extract_dir}"]
        if password:
          command.append(f"-p{password}")

        try:
          result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, timeout=max_seconds)
        except FileNotFoundError:
          self.logger.error(
              f"Failed to extract archive '{archive_name}': '7z' binary not found on PATH",
              extra={
                  "event_type": "ARCHIVE_TOOL_MISSING",
                  "step": self.step_name,
                  "email_id": getattr(email, "id", None),
                  "workflow_id": context.get("workflow_id"),
                  "run_id": context.get("run_id"),
              },
          )
          return []
        except subprocess.TimeoutExpired:
          last_error = f"timed out after {max_seconds}s"
          continue

        if result.returncode == 0:
          members = []
          for entry in os.listdir(extract_dir):
            entry_path = os.path.join(extract_dir, entry)
            if os.path.isfile(entry_path):
              with open(entry_path, "rb") as fh:
                members.append((entry, fh.read()))
          return members

        last_error = f"7z exit code {result.returncode}"
        for entry in os.listdir(extract_dir):
          entry_path = os.path.join(extract_dir, entry)
          if os.path.isfile(entry_path):
            os.remove(entry_path)

    self.logger.error(
        f"Failed to extract archive '{archive_name}': all password attempts failed ({last_error})",
        extra={
            "event_type": "ARCHIVE_EXTRACT_FAILED",
            "step": self.step_name,
            "email_id": getattr(email, "id", None),
            "workflow_id": context.get("workflow_id"),
            "run_id": context.get("run_id"),
        },
    )
    return []
