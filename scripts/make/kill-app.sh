#!/bin/bash
# Stops the app (backend + frontend dev servers + db).
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

pkill -f "uvicorn mailextractor.backend.main:app" || true
pkill -f "frontend/node_modules/.bin/vite" || true
pkill -f "scripts/webserver-dev.sh" || true

bash "$MAKE_DIR/db-down.sh"
