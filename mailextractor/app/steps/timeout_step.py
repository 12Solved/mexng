from datetime import datetime

from sqlalchemy.orm import object_session

from mailextractor import models

from .base_step import Step


class TimeoutStep(Step):
    """
    Records that a named checkpoint has been touched by an incoming email.
    On first execution the checkpoint is created with next_expected_at set to
    reference_timestamp. Subsequent executions only update last_seen_at; the
    background checker (check_checkpoints.py) is responsible for evaluating
    whether the arrival was on time and for advancing next_expected_at.
    """

    category = "control"
    node_type = "default"
    args_in = {"email": "Email"}
    args_out = []
    config_schema = {
        "checkpoint": {
            "type": "string",
            "required": True,
            "label": "Checkpoint name",
            "placeholder": "e.g. weekly-invoice",
        },
        "reference_timestamp": {
            "type": "datetime",
            "required": True,
            "label": "First expected time (UTC)",
        },
        "normal_interval_hours": {
            "type": "duration",
            "required": True,
            "label": "Normal interval",
        },
        "late_interval_hours": {
            "type": "duration",
            "required": False,
            "label": "Late interval",
        },
        "timezone": {
            "type": "string",
            "required": False,
            "label": "Timezone",
            "default": "UTC",
            "options": [
                "UTC",
                "Europe/London",
                "Europe/Berlin",
                "Europe/Paris",
                "Europe/Helsinki",
                "Europe/Athens",
                "Europe/Istanbul",
                "US/Eastern",
                "US/Central",
                "US/Mountain",
                "US/Pacific",
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "America/Sao_Paulo",
                "Asia/Dubai",
                "Asia/Kolkata",
                "Asia/Bangkok",
                "Asia/Singapore",
                "Asia/Tokyo",
                "Asia/Shanghai",
                "Australia/Sydney",
                "Pacific/Auckland",
            ],
        },
    }

    def execute(self, context):
        email = context.get("email")
        session = object_session(email)
        if not session:
            raise RuntimeError("TimeoutStep requires a DB session attached to the email object")

        name = self.config["checkpoint"]
        raw_reference = self.config["reference_timestamp"]
        try:
            reference_timestamp = datetime.fromisoformat(raw_reference.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"TimeoutStep: invalid reference_timestamp {raw_reference!r}. "
                "Expected ISO 8601 string, e.g. '2024-01-01T09:00:00Z'."
            ) from exc
        normal_interval_hours = self.config["normal_interval_hours"]
        late_interval_hours = self.config.get("late_interval_hours")
        timezone = self.config.get("timezone", "UTC")
        workflow_id = context.get("workflow_id")
        now = datetime.utcnow()

        checkpoint = session.query(models.Checkpoint).filter(models.Checkpoint.name == name).first()
        if checkpoint is None:
            # Create the checkpoint; next_expected_at starts at reference_timestamp.
            # The checker will advance it once that deadline passes.
            checkpoint = models.Checkpoint(
                name=name,
                reference_timestamp=reference_timestamp,
                normal_interval_hours=normal_interval_hours,
                late_interval_hours=late_interval_hours,
                next_expected_at=reference_timestamp,
                timezone=timezone,
                workflow_id=workflow_id,
                last_seen_at=now,
                status="never_seen",
            )
            session.add(checkpoint)
        else:
            # Only stamp the arrival time. The checker decides on-time vs late
            # and advances next_expected_at on its next run.
            checkpoint.last_seen_at = now
            checkpoint.timezone = timezone
            checkpoint.workflow_id = workflow_id
            checkpoint.updated_at = now

        session.commit()

        self.logger.info(
            f"Checkpoint '{name}' touched",
            extra={
                "event_type": "CHECKPOINT_TOUCHED",
                "step": self.step_name,
                "email_id": getattr(email, "id", None),
                "workflow_id": workflow_id,
                "run_id": context.get("run_id"),
            },
        )
