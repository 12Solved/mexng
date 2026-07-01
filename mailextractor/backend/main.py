import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from sqlalchemy import text

from mailextractor.backend.db import engine
from mailextractor.backend.routes import (
    checkpoints,
    emails,
    logs,
    runs,
    stats,
    steps,
    workflows,
)
from mailextractor.models import Base


# def _init_db() -> None:
#     # Use a PostgreSQL advisory lock so that when multiple uvicorn workers start
#     # simultaneously they don't race to CREATE TYPE / CREATE TABLE.
#     with engine.connect() as conn, conn.begin():
#         conn.execute(text("SELECT pg_advisory_xact_lock(1234567890)"))
#         Base.metadata.create_all(bind=engine)


# _init_db()

app = FastAPI()
add_pagination(app)

_origins = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails.router)
app.include_router(logs.router)
app.include_router(runs.router)
app.include_router(workflows.router)
app.include_router(checkpoints.router)
app.include_router(steps.router)
app.include_router(stats.router)
