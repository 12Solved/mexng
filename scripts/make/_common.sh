#!/bin/bash
# Shared helpers for scripts/make/*.sh — source this, don't run it directly.

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." &> /dev/null && pwd)

activate_env() {
	source "$ROOT_DIR/.venv/bin/activate"
	source "$ROOT_DIR/.nenv/bin/activate"
	set -a
	source "$ROOT_DIR/.env"
	set +a
}
