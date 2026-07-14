from .base_step import Step

TRUE_LITERALS = {"true", "1", "yes", "on", "enable", "enabled"}
FALSE_LITERALS = {"false", "0", "no", "off", "disable", "disabled"}


class SetVariableStep(Step):

  """
  Sets an arbitrary context variable, including reserved control keys such
  as '@dry_run' or '@stop'. See docs/workflow.md for examples and the
  security note on control-key access.
  """

  category = "control"
  node_type = "default"
  args_in = {}
  args_out = []
  config_schema = {
      "name": {
          "type": "string",
          "required": True,
          "label": "Variable name",
          "placeholder": "e.g. invoice_id, @dry_run, @stop",
          "description": "Context key to set. May be an existing '@' control key.",
      },
      "value": {
          "type": "string",
          "required": True,
          "label": "Value",
          "placeholder": "e.g. ${email_sender}, disable, 42",
          "description": "Literal value or a ${variable} reference to one already in context.",
      },
      "value_type": {
          "type": "string",
          "required": False,
          "label": "Value type",
          "default": "string",
          "options": ["string", "boolean", "integer", "float"],
          "description": "Coerces the resolved value before storing it, e.g. so '@dry_run' behaves as a real boolean.",
      },
      "only_if_unset": {
          "type": "string",
          "required": False,
          "label": "Only set if unset",
          "default": "false",
          "options": ["false", "true"],
          "description": "If true, skip setting when the variable is already present in context.",
      },
  }

  def execute(self, context):
    name = (self.config.get("name") or "").strip()
    if not name:
      raise ValueError("SetVariableStep: 'name' is required.")

    if self._to_bool(self.config.get("only_if_unset", "false")) and context.has(name):
      self.logger.debug(
        f"SetVariableStep: '{name}' already set, skipping",
        extra={
            "event_type": "SET_VARIABLE_SKIPPED",
            "step": self.step_name,
            "workflow_id": context.get("workflow_id"),
            "run_id": context.get("run_id"),
        }
      )
      return

    value_type = (self.config.get("value_type") or "string").strip().lower()
    value = self._coerce(self.config.get("value", ""), value_type, name)

    context.set(name, value)

    self.logger.info(
      f"Set context variable '{name}' = {value!r}",
      extra={
          "event_type": "SET_VARIABLE",
          "step": self.step_name,
          "workflow_id": context.get("workflow_id"),
          "run_id": context.get("run_id"),
      }
    )

  def _coerce(self, raw_value, value_type, name):
    if value_type == "string":
      return raw_value

    if value_type == "boolean":
      return self._to_bool(raw_value, name)

    if value_type == "integer":
      try:
        return int(raw_value)
      except (TypeError, ValueError) as exc:
        raise ValueError(
          f"SetVariableStep: value {raw_value!r} for '{name}' is not a valid integer."
        ) from exc

    if value_type == "float":
      try:
        return float(raw_value)
      except (TypeError, ValueError) as exc:
        raise ValueError(
          f"SetVariableStep: value {raw_value!r} for '{name}' is not a valid float."
        ) from exc

    raise ValueError(f"SetVariableStep: unknown value_type {value_type!r}.")

  def _to_bool(self, raw_value, name=None):
    if isinstance(raw_value, bool):
      return raw_value

    literal = str(raw_value).strip().lower()
    if literal in TRUE_LITERALS:
      return True
    if literal in FALSE_LITERALS:
      return False

    raise ValueError(
      f"SetVariableStep: value {raw_value!r}"
      + (f" for '{name}'" if name else "")
      + " is not a valid boolean. Use one of "
      f"{sorted(TRUE_LITERALS | FALSE_LITERALS)}."
    )
