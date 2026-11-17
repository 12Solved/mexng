from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import Session

from mailextractor import models
from mailextractor.backend.utils.alert_rule_targets import PATTERN_FIELDS, TARGET_PAIRS, check_targets
from mailextractor.backend.utils.regex import check_pg_regex


def _to_columns(fields: dict) -> dict:
    # The API's LogLevel and the model's are separate enums.
    if "min_level" in fields:
        return {**fields, "min_level": models.LogLevel[fields["min_level"].value]}
    return fields


def _check_patterns(db: Session, fields: dict):
    # check_logs runs these with Postgres ~ / ~*, so Postgres has to accept them.
    for pattern_field in PATTERN_FIELDS:
        pattern = fields.get(pattern_field)
        if pattern is not None:
            try:
                check_pg_regex(db, pattern)
            except ValueError as e:
                raise ValueError(f"{e} ({pattern_field})") from e


def get_alert_rules(db: Session, user_id: int):
    return paginate(
        db,
        select(models.AlertRule).where(models.AlertRule.user_id == user_id).order_by(models.AlertRule.id),
    )


def get_alert_rule(db: Session, rule_id: int, user_id: int):
    return (
        db.query(models.AlertRule)
        .filter(models.AlertRule.id == rule_id, models.AlertRule.user_id == user_id)
        .first()
    )


def create_alert_rule(db: Session, user_id: int, fields: dict):
    check_targets(fields)
    _check_patterns(db, fields)
    rule = models.AlertRule(user_id=user_id, **_to_columns(fields))
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_alert_rule(db: Session, rule_id: int, user_id: int, fields: dict):
    rule = get_alert_rule(db, rule_id, user_id)
    if not rule:
        return None
    # A partial update can pair a new pattern with an exact filter already stored on the rule.
    check_targets({name: fields.get(name, getattr(rule, name)) for pair in TARGET_PAIRS for name in pair})
    _check_patterns(db, fields)
    for name, value in _to_columns(fields).items():
        setattr(rule, name, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_alert_rule(db: Session, rule_id: int, user_id: int):
    rule = get_alert_rule(db, rule_id, user_id)
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True
