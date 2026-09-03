from fastapi import Depends
from sqlalchemy.orm import Session

from mailextractor.backend.db import get_db
from mailextractor.models import User
from mailextractor.users import get_default_user


def current_user(db: Session = Depends(get_db)) -> User:
    """The user making the current request."""
    return get_default_user(db)
