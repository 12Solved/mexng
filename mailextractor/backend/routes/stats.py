import asyncio
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from mailextractor.backend.db import get_db, SessionLocal
from mailextractor.backend.services import stat_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/")
def get_stats(
    db: Session = Depends(get_db),
    period: str | None = Query(None, description="last_24h, last_7d, last_28d, or all"),
):
    return stat_service.get_stats(db, period)


@router.get("/stream")
async def stream_stats(
    period: str | None = Query(None, description="last_24h, last_7d, last_28d, or all"),
):
    async def event_generator():
        try:
            while True:
                db = SessionLocal()
                try:
                    data = stat_service.get_stats(db, period)
                finally:
                    db.close()
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
