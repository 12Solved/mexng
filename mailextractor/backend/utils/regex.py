"""
Shared regex validation. Check a pattern with the engine that will run it:
Python's `re` and Postgres's regex flavour accept slightly different syntax
(e.g. `(?P<name>...)` is valid in Python but rejected by Postgres).
"""
import re

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

# SQLSTATE for invalid_regular_expression.
_PG_INVALID_REGEX = "2201B"


def check_regex(pattern: str) -> None:
    """Raise ValueError if Python's `re` can't compile `pattern` (for patterns run in Python)."""
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex: {e}") from e


def pg_regex_error(e: DBAPIError) -> str | None:
    """"Invalid regex: <reason>" if `e` is Postgres rejecting a regex, else None.

    For queries that run user patterns directly: catch DBAPIError around the
    query and turn this into a user-facing error instead of a 500."""
    if getattr(e.orig, "pgcode", None) != _PG_INVALID_REGEX:
        return None
    # psycopg2's message is "invalid regular expression: <reason>" plus a trailing newline.
    reason = str(e.orig).strip().removeprefix("invalid regular expression: ")
    return f"Invalid regex: {reason}"


def check_pg_regex(db: Session, pattern: str) -> None:
    """Raise ValueError if Postgres can't compile `pattern`. For patterns that are
    stored now and run with ~ / ~* later (e.g. alert rules)."""
    try:
        # Savepoint, so a rejected pattern doesn't abort the caller's transaction.
        with db.begin_nested():
            db.execute(text("SELECT '' ~ :pattern"), {"pattern": pattern})
    except DBAPIError as e:
        error = pg_regex_error(e)
        if error is None:
            raise
        raise ValueError(error) from e
