UV ?= uv
PYTHON := .venv/bin/python

.PHONY: setup postgres seed test lint dev demo capture clean

setup:
	$(UV) sync --extra dev
	docker compose up -d --wait postgres
	$(PYTHON) -m concord.storage.db

postgres:
	docker compose up -d --wait postgres

seed:
	$(PYTHON) -m concord.seed.seed_duckdb

test:
	docker compose up -d --wait postgres
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check backend tests
	$(PYTHON) -m ruff format --check backend tests

dev:
	$(PYTHON) -m uvicorn concord.api.main:app --reload

demo: postgres seed
	$(PYTHON) -m concord.demo

capture:
	@echo "Cloud capture is disabled in P0 and will require explicit ALLOW_CLOUD=true in Phase P5."
	@exit 1

clean:
	rm -f data/concord_iq.duckdb
