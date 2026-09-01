"""Shared fixtures for the poll/process pipeline tests.

Tests run against a *separate* Postgres database (same server as
DATABASE_URL, name suffixed with `_test`) so they never touch dev data.
The db is created on first use and its tables truncated before every test.
"""
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from mailextractor.models import Base, WorkflowModel  # noqa: E402

EXAMPLE_DATA_DIR = os.path.join(ROOT_DIR, "example-data")

TABLES = ["logs", "runs", "workflows", "attachments", "emails", "mailbox_state", "checkpoints"]


TEST_DATABASE_NAME = "db_test"


def _test_database_url():
    # Fixed name rather than "<dev db name>_test" so it doesn't vary per
    # developer's DATABASE_URL and stays easy to spot/drop.
    base_url = os.environ["DATABASE_URL"]
    prefix, _, _dbname = base_url.rpartition("/")
    return f"{prefix}/{TEST_DATABASE_NAME}"


TEST_DATABASE_URL = _test_database_url()


def _ensure_test_database_exists():
    admin_url = os.environ["DATABASE_URL"]
    test_dbname = TEST_DATABASE_URL.rsplit("/", 1)[-1]
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": test_dbname},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{test_dbname}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def test_engine():
    _ensure_test_database_exists()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    with test_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE {} RESTART IDENTITY CASCADE".format(", ".join(TABLES))))
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@dataclass
class FakeConfig:
    """Stands in for mailextractor.app.config.config — poll()/process()/get_provider()
    take a config object as a parameter, so tests can inject one pointed at the test db
    without touching the real .env-backed singleton."""
    DATABASE_URL: str
    EMAIL_PROVIDER: str = "glob"
    GLOB_PATTERNS: str = ""
    CHECKPOINT_PATH: str = "checkpoint.txt"
    FILE_EXTRACT_PATH: str = "/"
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USERNAME: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_USE_SSL: bool = True
    IMAP_MAILBOX: str = "INBOX"


@pytest.fixture
def make_config(tmp_path):
    def _make(**overrides):
        checkpoint_path = overrides.pop("CHECKPOINT_PATH", str(tmp_path / "checkpoint.txt"))
        return FakeConfig(DATABASE_URL=TEST_DATABASE_URL, CHECKPOINT_PATH=checkpoint_path, **overrides)
    return _make


@pytest.fixture
def insert_workflow(db_session):
    def _insert(workflow_json, name=None, enabled=True):
        model = WorkflowModel(
            name=name or workflow_json.get("name", "test-workflow"),
            workflow_json=workflow_json,
            enabled=enabled,
        )
        db_session.add(model)
        db_session.commit()
        return model
    return _insert


def _patch_save_destinations(steps, new_root):
    """Rewrites every save_attachment_step's destination to live under new_root,
    so tests don't write into the repo's ./out/... like the example workflows do."""
    for step in steps:
        if step.get("type") == "save_attachment_step":
            dest = step["config"]["destination"].lstrip("./")
            step["config"]["destination"] = f"{new_root}/{dest}"
        if "steps" in step:
            _patch_save_destinations(step["steps"], new_root)


@pytest.fixture
def load_workflows(insert_workflow):
    def _load(*workflow_files, patch_destination=None):
        loaded = []
        for filename in workflow_files:
            path = os.path.join(EXAMPLE_DATA_DIR, "workflows", filename)
            with open(path) as f:
                workflow_json = json.load(f)
            if patch_destination is not None:
                _patch_save_destinations(workflow_json.get("steps", []), patch_destination)
            loaded.append(insert_workflow(workflow_json, name=workflow_json.get("name", filename)))
        return loaded
    return _load
