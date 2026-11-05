from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mailextractor.models import User


def set_email(db: Session, user: User, email: str | None):
    """Returns None when another user already has this email."""
    user.email = email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(user)
    return user
