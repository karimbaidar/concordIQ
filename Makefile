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
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check backend tests
	$(PYTHON) -m ruff format --check backend tests

dev:
	@echo "The API and frontend are scheduled for later phases; P0 provides data and storage foundations."

demo:
	@echo "The headless reconciliation demo is scheduled for Phase P3."
	@exit 1

capture:
	@echo "Cloud capture is disabled in P0 and will require explicit ALLOW_CLOUD=true in Phase P5."
	@exit 1

clean:
	rm -f data/concord_iq.duckdb
