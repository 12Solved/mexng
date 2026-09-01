import re

from sqlalchemy import and_, or_


def build_filter(model, group: dict):
  combinator = group.get("combinator", "and")
  clauses = []

  for rule in group.get("rules", []):
    if "rules" in rule:
      clauses.append(build_filter(model, rule))
      continue

    col = getattr(model, rule["field"], None)
    if col is None:
      continue

    op  = rule["operator"]
    val = rule["value"]

    match op:
      case "contains":
        clauses.append(col.ilike(f"%{val}%"))
      case "doesNotContain":
        clauses.append(~col.ilike(f"%{val}%"))
      case "beginsWith":
        clauses.append(col.ilike(f"{val}%"))
      case "endsWith":
        clauses.append(col.ilike(f"%{val}"))
      case "=":
        clauses.append(col == val)
      case "!=":
        clauses.append(col != val)
      case "<":
        clauses.append(col < val)
      case ">":
        clauses.append(col > val)
      case "<=":
        clauses.append(col <= val)
      case ">=":
        clauses.append(col >= val)
      case "matches":
        try:
          re.compile(val)
        except re.error as e:
          raise ValueError(f"Invalid regex for field '{rule['field']}': {e}") from e
        clauses.append(col.op("~*")(val))

  return and_(*clauses) if combinator == "and" else or_(*clauses)
