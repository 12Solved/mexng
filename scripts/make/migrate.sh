#!/bin/bash
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

source .venv/bin/activate
set -a
source .env
set +a

alembic upgrade head
