UV ?= uv
PNPM ?= pnpm
PYTHON := .venv/bin/python

.PHONY: setup postgres seed test lint dev frontend demo agent-smoke capture clean

setup:
	$(UV) sync --extra dev
	$(PNPM) --dir frontend install --frozen-lockfile
	docker compose up -d --wait postgres
	$(PYTHON) -m concord.storage.db

postgres:
	docker compose up -d --wait postgres

seed:
	$(PYTHON) -m concord.seed.seed_duckdb

test:
	docker compose up -d --wait postgres
	$(PYTHON) -m pytest
	$(PNPM) --dir frontend test

lint:
	$(PYTHON) -m ruff check backend tests
	$(PYTHON) -m ruff format --check backend tests
	$(PNPM) --dir frontend lint

frontend:
	$(PNPM) --dir frontend dev

dev: postgres seed
	@set -e; \
	$(PYTHON) -m uvicorn concord.api.main:app --reload & \
	api_pid=$$!; \
	trap 'kill $$api_pid 2>/dev/null || true' EXIT INT TERM; \
	$(PNPM) --dir frontend dev

demo: postgres seed
	$(PYTHON) -m concord.demo

agent-smoke: postgres seed
	PYTHONWARNINGS="ignore::FutureWarning" \
	$(PYTHON) -c "from concord.ms_agent.workflow import main; main()" \
		--term "Active Customer" \
		--period "2026-03-04/2026-06-01" \
		--provider local

capture:
	$(PYTHON) -m concord.capture

clean:
	rm -f data/concord_iq.duckdb
	rm -rf frontend/dist
