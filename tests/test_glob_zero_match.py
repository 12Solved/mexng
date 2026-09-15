"""A GLOB_PATTERNS entry with zero currently-matching
files (the normal steady state between drops) makes GLOBProvider append the
raw, unexpanded pattern string as if it were a literal path; _parse_message
then fails "File not found" and poll() raises/rolls back instead of treating
it as zero new emails."""
import os

from mailextractor.app.poller.poller import poll


def test_glob_pattern_with_no_matches_is_not_an_error(make_config, db_session, tmp_path):
    empty_pattern = str(tmp_path / "*.eml")  # tmp_path has no .eml files in it
    config = make_config(EMAIL_PROVIDER="glob", GLOB_PATTERNS=empty_pattern)

    poll(config)  # must NOT raise — zero matches is a normal, quiet no-op

    from mailextractor.models import Email
    assert db_session.query(Email).count() == 0
