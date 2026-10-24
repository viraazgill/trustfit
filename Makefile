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

.PHONY: install dev db test test-reference test-engine test-api lint seed

install:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "packages/trustfit_engine[dev]" -e "apps/api[dev]"
	cd $(WEB) && npm ci

db:
	docker compose up -d --wait db

dev: db
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
	cd $(WEB) && npm run lint

# Placeholder until phase 2 adds the seed loader (python -m app.seed --reset).
seed:
	@echo "seed: not implemented yet (phase 2)"
