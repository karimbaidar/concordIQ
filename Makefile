UV ?= uv
PNPM ?= pnpm
PYTHON := .venv/bin/python

.PHONY: setup postgres seed test lint dev frontend demo scan eval agent-smoke \
	foundry-agent-dry-run foundry-agent-smoke foundry-hosted-dry-run \
	foundry-hosted-package foundry-hosted-smoke capture fabric-mcp-diagnose \
	fabric-bootstrap-dry-run fabric-bootstrap replay-check clean

FOUNDRY_AGENT_PROVIDER ?= local
FOUNDRY_AGENT_WORKFLOW_MODE ?= strict

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

scan: seed
	$(PYTHON) -m concord.scan

eval: postgres seed
	$(PYTHON) -m concord.evals

agent-smoke: postgres seed
	PYTHONWARNINGS="ignore::FutureWarning" \
	$(PYTHON) -c "from concord.ms_agent.workflow import main; main()" \
		--term "Active Customer" \
		--period "2026-03-04/2026-06-01" \
		--provider local

foundry-agent-dry-run:
	PROVIDER=local ALLOW_CLOUD=false MAX_CLOUD_CALLS=0 \
	$(UV) run --extra dev --extra foundry-hosting \
		python -m concord.ms_agent.foundry_hosted_entrypoint \
		--dry-run \
		--provider local \
		--workflow-mode $(FOUNDRY_AGENT_WORKFLOW_MODE)

foundry-agent-smoke: postgres seed
	PROVIDER=$(FOUNDRY_AGENT_PROVIDER) ALLOW_CLOUD=false MAX_CLOUD_CALLS=0 \
	$(UV) run --extra dev --extra foundry-hosting \
		python -m concord.ms_agent.foundry_hosted_entrypoint \
		--smoke \
		--provider $(FOUNDRY_AGENT_PROVIDER) \
		--workflow-mode $(FOUNDRY_AGENT_WORKFLOW_MODE)

foundry-hosted-dry-run:
	$(PYTHON) -m concord.ms_agent.foundry_hosted --dry-run

foundry-hosted-package:
	$(PYTHON) -m concord.ms_agent.foundry_hosted --package

foundry-hosted-smoke:
	$(PYTHON) -m concord.ms_agent.foundry_hosted --smoke

capture:
	$(PYTHON) -m concord.capture

fabric-mcp-diagnose:
	$(PYTHON) -m concord.fabric_mcp_diagnose

fabric-bootstrap-dry-run:
	$(PYTHON) -m concord.fabric_bootstrap --dry-run

fabric-bootstrap:
	$(PYTHON) -m concord.fabric_bootstrap

replay-check:
	$(PYTHON) -m concord.replay_check
	PROVIDER=replay ALLOW_CLOUD=false MAX_CLOUD_CALLS=0 $(MAKE) demo

clean:
	rm -f data/concord_iq.duckdb
	rm -rf frontend/dist
