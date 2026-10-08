from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mailextractor.models import User

def get_or_create_user(db: Session, name: str) -> User:
    """Return the user with this name, creating it if it doesn't exist yet."""
    user = db.query(User).filter_by(name=name).first()
    if user is None:
        user = User(name=name)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Another process created it concurrently.
            db.rollback()
            user = db.query(User).filter_by(name=name).one()
    return user

def get_default_user(db: Session) -> User:
    """Return the single default user, creating it if it doesn't exist yet."""
    return get_or_create_user(db, "default")
