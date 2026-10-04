# Convenience commands. Run `make help`.
SHELL := /bin/bash
PY := backend/.venv/bin

.PHONY: help setup infra migrate seed api worker web dev test lint fmt eval

help:            ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:           ## Create the Python venv and install backend + frontend dependencies
	cd backend && python3.12 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e ".[dev]"
	[ -f backend/.env ] || cp backend/.env.example backend/.env
	cd frontend && npm install

infra:           ## Start Postgres + Redis in Docker (optional; or use Homebrew services)
	docker compose up -d db redis

migrate:         ## Apply database migrations
	cd backend && .venv/bin/alembic upgrade head

seed:            ## Load demo users, workspaces, documents and chats (RESET=1 to recreate)
	cd backend && .venv/bin/python -m app.cli seed $(if $(RESET),--reset,)

api:             ## Run the API with auto-reload on :8000
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 --timeout-graceful-shutdown 3

worker:          ## Run the ingestion worker
	cd backend && .venv/bin/arq app.workers.settings.WorkerSettings

web:             ## Run the frontend on :5173
	cd frontend && npm run dev

dev:             ## Run API, worker and frontend together (Ctrl+C stops all)
	@trap 'kill 0' EXIT; $(MAKE) api & $(MAKE) worker & $(MAKE) web & wait

test:            ## Run all tests (backend needs TEST_DATABASE_URL / TEST_REDIS_URL or local defaults)
	cd backend && .venv/bin/pytest --cov
	cd frontend && npm test

lint:            ## Lint and type-check everything
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app
	cd frontend && npm run lint && npm run typecheck

fmt:             ## Auto-format everything
	cd backend && .venv/bin/ruff check --fix . && .venv/bin/ruff format .
	cd frontend && npm run format
