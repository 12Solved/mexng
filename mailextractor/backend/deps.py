from fastapi import Depends, Request
from sqlalchemy.orm import Session

from mailextractor.backend.db import get_db
from mailextractor.models import User
from mailextractor.users import get_or_create_user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """The user making the current request, as identified by AuthMiddleware."""
    return get_or_create_user(db, request.state.username)
