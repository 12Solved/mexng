"""poll() used to create a brand-new SQLAlchemy engine/pool on every call and
never dispose it — harmless for a one-shot invocation (the process exits
right after), but a real connection leak under --loop, where poll() runs on
every scheduler tick inside one long-lived process. Fixed by letting an
engine be passed in (disposed by the caller, not poll()) while poll() still
creates+disposes its own by default — required so each test stays isolated
to its own config's db rather than a shared/global engine.
"""
from unittest.mock import Mock, patch

from sqlalchemy import create_engine as real_create_engine

import mailextractor.app.poller.poller as poller_module
from mailextractor.app.poller.poller import poll


def _glob_config(make_config, tmp_path):
    return make_config(EMAIL_PROVIDER="glob", GLOB_PATTERNS=str(tmp_path / "*.eml"))


def test_poll_disposes_its_own_engine_when_it_creates_one(make_config, db_session, tmp_path):
    config = _glob_config(make_config, tmp_path)

    real_engine = real_create_engine(config.DATABASE_URL)
    real_engine.dispose = Mock(wraps=real_engine.dispose)

    with patch.object(poller_module, "create_engine", return_value=real_engine) as mock_create_engine:
        poll(config)

    mock_create_engine.assert_called_once()
    real_engine.dispose.assert_called_once()


def test_poll_does_not_dispose_an_externally_provided_engine(make_config, db_session, tmp_path):
    config = _glob_config(make_config, tmp_path)

    engine = real_create_engine(config.DATABASE_URL)
    engine.dispose = Mock(wraps=engine.dispose)

    poll(config, engine=engine)

    engine.dispose.assert_not_called()
    engine.dispose()  # real cleanup, now that we've confirmed poll() didn't do it
