from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import Session

from mailextractor import models


def _to_columns(fields: dict) -> dict:
    # The API's LogLevel and the model's are separate enums.
    if "min_level" in fields:
        return {**fields, "min_level": models.LogLevel[fields["min_level"].value]}
    return fields


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
    rule = models.AlertRule(user_id=user_id, **_to_columns(fields))
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_alert_rule(db: Session, rule_id: int, user_id: int, fields: dict):
    rule = get_alert_rule(db, rule_id, user_id)
    if not rule:
        return None
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
