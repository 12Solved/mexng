"""scripts/read_email.py's own documented usage
(`python scripts/read_email.py *.eml`) left the .eml paths in sys.argv, and
poller.main() (added for --loop in an earlier commit) parses sys.argv with
argparse — which rejects them as unrecognized arguments before poll() runs.
Runs as a real subprocess since the bug is specifically about argv handling
at the script entrypoint, not something a direct function call would hit."""
import os
import subprocess
import sys

from tests.conftest import TEST_DATABASE_URL

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT_DIR, "example-data", "emails", "invoice_report.eml")


def test_read_email_script_accepts_file_args(db_session):
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL

    result = subprocess.run(
        [sys.executable, "scripts/read_email.py", FIXTURE],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"

    from mailextractor.models import Email
    assert db_session.query(Email).filter(Email.message_id.like("%invoice4471%")).count() == 1
