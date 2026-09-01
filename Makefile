SHELL := /bin/bash

ENV = set -a && source .env && set +a
VENV = source .venv/bin/activate
NENV = source .nenv/bin/activate
ACTIVATE = $(VENV) && $(NENV) && $(ENV)

# ── Setup ─────────────────────────────────────────────────────────────────────

.PHONY: setup
setup: .env .venv .nenv frontend/node_modules db-up migrate

.env:
	cp .env.example .env
	@echo ".env created — fill in your credentials"

.venv:
	python -m venv .venv
	$(VENV) && pip install -r requirements.txt

.nenv:
	nodeenv -n 24.14.1 .nenv

frontend/node_modules:
	$(NENV) && cd frontend && npm install

.PHONY: db-up
db-up:
	docker-compose -f mailextractor/docker-compose.yml up -d

.PHONY: db-down
db-down:
	docker-compose -f mailextractor/docker-compose.yml down

.PHONY: migrate
migrate:
	$(VENV) && $(ENV) && alembic upgrade head

# ── Dev server ────────────────────────────────────────────────────────────────

.PHONY: dev
dev: db-up
	$(ACTIVATE) && bash scripts/webserver-dev.sh

.PHONY: down
down:
	-pkill -f "uvicorn mailextractor.backend.main:app"
	-pkill -f "frontend/node_modules/.bin/vite"
	-pkill -f "scripts/webserver-dev.sh"
	$(MAKE) db-down

# ── Email pipeline ────────────────────────────────────────────────────────────

.PHONY: poll
poll:
	$(ACTIVATE) && python mailextractor/app/poller/poller.py

.PHONY: process
process:
	$(ACTIVATE) && python mailextractor/app/processor/processor.py

.PHONY: run
run: poll process
