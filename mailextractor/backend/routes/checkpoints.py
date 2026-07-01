from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from mailextractor.backend import schemas
from mailextractor.backend.db import get_db
from mailextractor.backend.services import checkpoint_service

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


@router.get("/", response_model=Page[schemas.CheckpointSchema])
def list_checkpoints(db: Session = Depends(get_db)):
    return checkpoint_service.get_checkpoints(db)


@router.get("/{checkpoint_id}", response_model=schemas.CheckpointSchema)
def get_checkpoint(checkpoint_id: int, db: Session = Depends(get_db)):
    checkpoint = checkpoint_service.get_checkpoint(db, checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint


@router.delete("/{checkpoint_id}")
def delete_checkpoint(checkpoint_id: int, db: Session = Depends(get_db)):
    ok = checkpoint_service.delete_checkpoint(db, checkpoint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"ok": True}
