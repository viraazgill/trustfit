# TrustFit monorepo tasks. Needs a POSIX shell (Git Bash on Windows).
# First run:   make install            (or: make install PYTHON=/path/to/python3.12+)

PYTHON ?= python
ifeq ($(OS),Windows_NT)
VENV_BIN := .venv/Scripts
else
VENV_BIN := .venv/bin
endif
PY := $(VENV_BIN)/python
WEB := apps/web

.PHONY: install dev db migrate test test-reference test-engine test-api test-e2e lint seed types

install:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "packages/trustfit_engine[dev]" -e "apps/api[dev]"
	cd $(WEB) && npm ci

db:
	docker compose up -d --wait db

migrate:
	cd apps/api && ../../$(PY) -m alembic upgrade head

dev: db migrate
	@echo "API on http://localhost:8000/docs, web on http://localhost:3000"
	cd apps/api && ../../$(PY) -m uvicorn app.main:app --reload --port 8000 & \
	cd $(WEB) && npm run dev

test: test-reference test-engine test-api

test-reference:
	$(PY) reference/trustfit_reference.py --check

test-engine:
	cd packages/trustfit_engine && ../../$(PY) -m pytest -q

test-api:
	cd apps/api && ../../$(PY) -m pytest -q

lint:
	$(PY) -m ruff check packages apps/api db
	cd $(WEB) && npm run lint && npx tsc --noEmit

# Regenerate the web app's API types from FastAPI's OpenAPI schema (commit both files).
types:
	cd apps/api && ../../$(PY) -m app.openapi > ../web/lib/api/openapi.json
	cd $(WEB) && npx openapi-typescript lib/api/openapi.json -o lib/api/schema.d.ts

# Browser tests of the demo path. Needs Postgres (make db) and seeded data (make seed).
test-e2e:
	cd $(WEB) && npx playwright test

# Wipes every table and reloads Subros, the demo SME, the demo companies and the seed users.
seed: migrate
	cd apps/api && ../../$(PY) -m app.seed --reset
