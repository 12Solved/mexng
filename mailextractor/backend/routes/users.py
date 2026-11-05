from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.deps import current_user
from mailextractor.backend.services import user_service
from mailextractor.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserSchema)
def get_current_user(user: User = Depends(current_user)):
    return user


@router.patch("/me", response_model=schemas.UserSchema)
def update_current_user_email(body: schemas.UserEmailBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    updated = user_service.set_email(db, user, body.email)
    if not updated:
        raise HTTPException(status_code=409, detail="Email already in use")
    return updated
