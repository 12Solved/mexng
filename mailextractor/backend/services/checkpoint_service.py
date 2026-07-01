from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import Session

from mailextractor import models


def get_checkpoints(db: Session):
    return paginate(db, select(models.Checkpoint).order_by(models.Checkpoint.name))


def get_checkpoint(db: Session, checkpoint_id: int):
    return db.query(models.Checkpoint).filter(models.Checkpoint.id == checkpoint_id).first()


def delete_checkpoint(db: Session, checkpoint_id: int):
    checkpoint = db.query(models.Checkpoint).filter(models.Checkpoint.id == checkpoint_id).first()
    if not checkpoint:
        return False
    db.delete(checkpoint)
    db.commit()
    return True
