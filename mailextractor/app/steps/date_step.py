from datetime import datetime, timedelta

from mailextractor.app.resolver import Resolver

from .base_step import Step


class DateStep(Step):

  """
  Computes a date/time (now, the email's date, or an explicit/referenced
  value), applies an optional day/hour offset, and formats it via strftime
  into a configurable context variable. See docs/workflow.md for examples.
  """

  category = "extraction"
  node_type = "default"
  args_in = {"email": "Email"}
  args_out = {"computed_date": "string"}
  config_schema = {
      "source": {
          "type": "string",
          "required": False,
          "label": "Base date/time",
          "default": "now",
          "placeholder": "now | email_date | 2024-01-15T00:00:00Z | ${some_var}",
          "description": (
              "'now', 'email_date', an ISO 8601 string, or a ${variable} "
              "reference to one already in context."
          ),
      },
      "offset_days": {
          "type": "string",
          "required": False,
          "label": "Offset (days)",
          "default": "0",
          "placeholder": "e.g. -1, 0, 7",
      },
      "offset_hours": {
          "type": "string",
          "required": False,
          "label": "Offset (hours)",
          "default": "0",
          "placeholder": "e.g. -12, 0, 6",
      },
      "format": {
          "type": "string",
          "required": False,
          "label": "Output format (strftime)",
          "default": "%Y-%m-%d",
          "placeholder": "%Y-%m-%d",
          "description": "Python strftime directives, e.g. %Y-%m-%d, %Y%m%d_%H%M%S, %B %d, %Y.",
      },
      "output_var": {
          "type": "string",
          "required": False,
          "label": "Output variable name",
          "default": "computed_date",
          "placeholder": "computed_date",
          "description": "Context key the formatted value is stored under, usable elsewhere as ${this_name}.",
      },
  }

  def execute(self, context):
    email = context.get("email")
    resolver = Resolver()

    raw_source = self.config.get("source") or "now"
    source = resolver.resolve(raw_source, context.data).strip()

    if source.lower() == "now":
      base = datetime.now()
    elif source.lower() == "email_date":
      if not email or not email.date:
        self.logger.warning(
          "DateStep: email has no date, stopping branch",
          extra={
              "event_type": "DATE_STEP_MISSING_EMAIL_DATE",
              "step": self.step_name,
              "email_id": getattr(email, "id", None),
              "workflow_id": context.get("workflow_id"),
              "run_id": context.get("run_id"),
          }
        )
        context.set("@stop", True)
        return
      base = email.date
    else:
      try:
        base = datetime.fromisoformat(source.replace("Z", "+00:00")).replace(tzinfo=None)
      except (ValueError, AttributeError) as exc:
        raise ValueError(
          f"DateStep: invalid 'source' {raw_source!r} (resolved to {source!r}). "
          "Expected 'now', 'email_date', or an ISO 8601 string, e.g. '2024-01-01T09:00:00Z'."
        ) from exc

    try:
      offset_days = int(self.config.get("offset_days") or 0)
      offset_hours = int(self.config.get("offset_hours") or 0)
    except (TypeError, ValueError) as exc:
      raise ValueError("DateStep: 'offset_days' and 'offset_hours' must be integers.") from exc

    base = base + timedelta(days=offset_days, hours=offset_hours)

    date_format = self.config.get("format") or "%Y-%m-%d"
    try:
      formatted = base.strftime(date_format)
    except (ValueError, TypeError) as exc:
      raise ValueError(f"DateStep: invalid strftime format {date_format!r}.") from exc

    output_var = self.config.get("output_var") or "computed_date"

    self.logger.info(
      f"Computed date '{formatted}' -> ${{{output_var}}}",
      extra={
          "event_type": "DATE_COMPUTED",
          "step": self.step_name,
          "email_id": getattr(email, "id", None),
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id"),
      }
    )

    context.set(output_var, formatted)
