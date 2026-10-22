import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from sqlalchemy import text

from mailextractor.app.app_logging.setup_logging import setup_logging
from mailextractor.backend.auth import AuthMiddleware
from mailextractor.backend.db import engine
from mailextractor.backend.routes import (
    checkpoints,
    emails,
    logs,
    runs,
    stats,
    steps,
    users,
    workflows,
)
from mailextractor.models import Base

setup_logging(engine)

app = FastAPI()
add_pagination(app)

app.add_middleware(AuthMiddleware)

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
app.include_router(users.router)
