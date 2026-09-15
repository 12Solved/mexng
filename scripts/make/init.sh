#!/bin/bash
# Initializes the project from 0 — run this after your first git pull/clone.
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
	cp .env.example .env
	echo ".env created — fill in your credentials"
fi

if [ ! -d .venv ]; then
	python -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
else
	source .venv/bin/activate
fi

if [ ! -d .nenv ]; then
	nodeenv -n 24.14.1 .nenv
fi
source .nenv/bin/activate

if [ ! -d frontend/node_modules ]; then
	(cd frontend && npm install)
fi

bash "$MAKE_DIR/db-up.sh"
bash "$MAKE_DIR/migrate.sh"

echo "Init complete."
