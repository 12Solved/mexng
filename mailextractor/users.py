from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mailextractor.models import User

def get_default_user(db: Session) -> User:
    """Return the single default user, creating it if it doesn't exist yet."""
    user = db.query(User).filter_by(name="default").first()
    if user is None:
        user = User(name="default")
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Another process created it concurrently.
            db.rollback()
            user = db.query(User).filter_by(name="default").one()
    return user
