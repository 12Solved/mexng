"""mailextractor/backend/utils/regex.py validation against Python's re and Postgres."""
import pytest
from sqlalchemy import text

from mailextractor.backend.utils.regex import check_pg_regex, check_regex


def test_check_regex_accepts_valid_pattern():
    check_regex(r"^Invoice #\d+")


def test_check_regex_rejects_invalid_pattern():
    with pytest.raises(ValueError, match="^Invalid regex: unterminated character set"):
        check_regex("([")


def test_check_pg_regex_accepts_valid_pattern(db_session):
    check_pg_regex(db_session, r"^Invoice #\d+")


def test_check_pg_regex_rejects_invalid_pattern(db_session):
    with pytest.raises(ValueError, match="^Invalid regex: "):
        check_pg_regex(db_session, "([")


def test_check_pg_regex_rejects_python_only_syntax(db_session):
    # Named groups are valid in Python but not in Postgres, which is what runs these patterns.
    check_regex("(?P<n>a)")
    with pytest.raises(ValueError, match="^Invalid regex: "):
        check_pg_regex(db_session, "(?P<n>a)")


def test_check_pg_regex_leaves_session_usable(db_session):
    with pytest.raises(ValueError):
        check_pg_regex(db_session, "([")
    assert db_session.execute(text("SELECT 1")).scalar() == 1
