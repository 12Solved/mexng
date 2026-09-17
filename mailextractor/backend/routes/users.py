from fastapi import APIRouter, Depends

from mailextractor.backend import schemas
from mailextractor.backend.deps import current_user
from mailextractor.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserSchema)
def get_current_user(user: User = Depends(current_user)):
    return user
