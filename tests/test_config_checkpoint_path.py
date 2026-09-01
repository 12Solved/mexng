"""config.py's CHECKPOINT_PATH must treat an empty env var as "unset" (safe
default) and only the explicit "none" sentinel as "no checkpoint" — an
accidentally-empty env var must not silently disable checkpointing in prod.
Runs as subprocesses since Config reads the env once at class-body/import time.
"""
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _checkpoint_path_for(env_value):
    env = os.environ.copy()
    if env_value is None:
        env.pop("CHECKPOINT_PATH", None)
    else:
        env["CHECKPOINT_PATH"] = env_value
    result = subprocess.run(
        [sys.executable, "-c", "from mailextractor.app.config import Config; print(repr(Config.CHECKPOINT_PATH))"],
        cwd=ROOT_DIR, env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return eval(result.stdout.strip())


def test_unset_checkpoint_path_defaults_to_checkpoint_txt():
    assert _checkpoint_path_for(None) == "checkpoint.txt"


def test_empty_checkpoint_path_falls_back_to_default_not_none():
    assert _checkpoint_path_for("") == "checkpoint.txt"


def test_none_sentinel_disables_checkpoint():
    assert _checkpoint_path_for("none") is None
    assert _checkpoint_path_for("None") is None
    assert _checkpoint_path_for("NONE") is None


def test_real_path_passes_through():
    assert _checkpoint_path_for("/app/data/checkpoint.txt") == "/app/data/checkpoint.txt"
