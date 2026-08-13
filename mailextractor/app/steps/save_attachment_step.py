import os

from sqlalchemy.orm import object_session
import mailextractor.app.steputils as stp

from .base_step import Step


from .base_step import Step


class SaveAttachmentStep(Step):

    """
    Saves the current attachment to disk at the configured destination path.
    Supports dynamic filename templating using ${attachment_name} and ${date} placeholders.
    Also updates the attachment's storage_path in the database after saving.
    """

    category = "io"
    node_type = "default"
    args_in = {"current": "Attachment"}
    args_out = {"saved_path": "string"}
    config_schema = {
        "destination": {
            "type": "string",
            "required": True,
            "label": "Destination folder",
            "placeholder": "e.g. /data/attachments",
        },
        "filename_template": {
            "type": "string",
            "required": False,
            "label": "Filename template",
            "placeholder": "${attachment_name}-${date}",
        }
    }

    def execute(self, context):

        attachment = context.get("current")
        email = context.get("email")
        if not attachment:
            self.logger.error(
                "Attachment missing in context",
                extra={
                    "event_type": "ATTACHMENT_MISSING",
                    "step": self.step_name,
                    "email_id": getattr(email, "id", None),
                    "workflow_id": context.get("workflow_id"),
                    "run_id": context.get("run_id", None),
                }
            )
            raise Exception()

        if not attachment.filename:
            attachment_basename = "unknown"
            ext = ".unk"
            attachment_name = "unknown.unk"
        else:
            attachment_basename, ext = os.path.splitext(attachment.filename)
            attachment_name = attachment.filename

        filename_template = self.config.get("filename_template", "${attachment_name}")

        # Build template context with all available variables
        template_context = {
            'attachment_basename': attachment_basename,
            'attachment_name': attachment_name,
            'ext': ext.lstrip('.'),  # Remove leading dot for easier templating
        }

        self.resolver = stp.Resolver()

        # Resolve destination path first
        resolved_destination = self.resolver.resolve(self.config["destination"], template_context)

        # Resolve filename
        new_filename = self.resolver.resolve(filename_template, template_context)

        if context.get("@dry_run"):
            resolved_path = os.path.join(resolved_destination, new_filename)
            self.logger.info(
                f"Dry-run: would save attachment to {resolved_path}",
                extra={
                    "event_type": "DRY_RUN_FILE_SAVE",
                    "step": self.step_name,
                    "attachment_id": getattr(attachment, "id", None),
                    "email_id": getattr(email, "id", None),
                    "workflow_id": context.get("workflow_id"),
                    "run_id": context.get("run_id", None),
                }
            )
            context.set("saved_path", resolved_path)
            return

        try:
            new_path = stp.secure_save_file(
                            os.path.join(
                                resolved_destination,
                                new_filename),
                            attachment.content,
                            create_parent=True)

        except PermissionError:
            self.logger.error(
                f"Permission denied when saving file to {resolved_destination}",
                extra={
                    "event_type": "FILE_PERMISSION_DENIED",
                    "step": self.step_name,
                    "attachment_id": getattr(attachment, "id", None),
                    "email_id": getattr(email, "id", None),
                    "workflow_id": context.get("workflow_id"),
                    "run_id": context.get("run_id", None),
                }
            )
            raise

        except Exception as e:
            self.logger.error(
                f"Failed to save attachment: {str(e)}",
                extra={
                    "event_type": "ATTACHMENT_SAVE_FAILED",
                    "step": self.step_name,
                    "attachment_id": getattr(attachment, "id", None),
                    "email_id": getattr(email, "id", None),
                    "workflow_id": context.get("workflow_id"),
                    "run_id": context.get("run_id", None),
                }
            )
            raise

        try:
            attachment.storage_path = new_path

            # object_session() raises for non-mapped objects (e.g. attachments
            # synthesized by extract_archive_step) instead of returning None.
            session = object_session(attachment) if hasattr(attachment, "_sa_instance_state") else None
            if session:
                session.commit()
            self.logger.info(
                f"Attachment saved to: {new_path}",
                extra={
                    "event_type": "FILE_SAVED_TO_PATH",
                    "step": self.step_name,
                    "attachment_id": getattr(attachment, "id", None),
                    "email_id": getattr(email, "id", None),
                    "workflow_id": context.get("workflow_id"),
                    "run_id": context.get("run_id", None),
                }
            )

        except Exception as e:
            self.logger.error(
                f"Failed to update attachment in DB: {str(e)}",
                extra={
                    "event_type": "DB_UPDATE_FAILED",
                    "step": self.step_name,
                    "attachment_id": getattr(attachment, "id", None),
                    "email_id": getattr(email, "id", None),
                    "workflow_id": context.get("workflow_id"),
                    "run_id": context.get("run_id", None),
                }
            )
            raise

        context.set("saved_path", new_path)
