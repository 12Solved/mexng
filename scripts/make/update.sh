#!/bin/bash
# Installs new dependencies and migrates the db — run this after every git pull.
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

source .venv/bin/activate
pip install -r requirements.txt

source .nenv/bin/activate
(cd frontend && npm install)

bash "$MAKE_DIR/migrate.sh"

echo "Update complete."
