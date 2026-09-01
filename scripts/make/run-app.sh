#!/bin/bash
# Runs the app (db + backend + frontend dev servers).
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

bash "$MAKE_DIR/db-up.sh"
activate_env
bash scripts/webserver-dev.sh
