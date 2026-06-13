UV ?= uv
PNPM ?= pnpm
PYTHON := .venv/bin/python

.PHONY: help setup postgres seed test test-backend test-frontend lint \
	dev dev-fresh dev-foundry dev-fabric dev-work-iq stop frontend \
	demo scan eval judge-proof cloud-proof semantic-pr-export work-iq-proof \
	fabric-proof foundry-hosted-smoke agent-smoke \
	foundry-agent-dry-run foundry-agent-smoke foundry-hosted-dry-run \
	foundry-hosted-package capture fabric-mcp-diagnose \
	fabric-bootstrap-dry-run fabric-bootstrap replay-check clean

FOUNDRY_AGENT_PROVIDER ?= local
FOUNDRY_AGENT_WORKFLOW_MODE ?= strict
LAUNCH := $(PYTHON) -m concord.dev_launcher

# ---------------------------------------------------------------------------
# help — the first command in the README
# ---------------------------------------------------------------------------
help:
	@echo "Concord IQ — make commands"
	@echo ""
	@echo "Start the application"
	@echo "  make setup         One-time local setup (deps, Postgres, schema, seed)"
	@echo "  make dev           Safe local UI (cloud disabled, always local)"
	@echo "  make dev-fresh     Reset synthetic demo state and start the cold-open UI"
	@echo "  make dev-foundry   Foundry-hosted UI (token acquired automatically)"
	@echo "  make dev-fabric    Live Fabric IQ UI (token acquired automatically)"
	@echo "  make dev-work-iq   Work IQ UI (MSAL delegated authentication)"
	@echo "  make stop          Stop only the Concord IQ dev processes"
	@echo "  make demo          Print the three deterministic scenario verdicts"
	@echo ""
	@echo "Verify the project"
	@echo "  make judge-proof   Reproducible mandatory judge proof"
	@echo "  make test          Backend + frontend tests"
	@echo "  make lint          Ruff + frontend lint/typecheck"
	@echo "  make eval          Deterministic safety scorecard"
	@echo ""
	@echo "Cloud proofs"
	@echo "  make cloud-proof          All configured live cloud proofs"
	@echo "  make foundry-hosted-smoke Foundry Agent Service hosted smoke"
	@echo "  make fabric-proof         Fabric IQ sanitized replay proof"
	@echo "  make work-iq-proof        Work IQ retrieval proof (honest status)"
	@echo "  make semantic-pr-export   SHA-256 content-hashed semantic-PR export"
	@echo ""
	@echo "Maintenance"
	@echo "  make seed          Reseed deterministic DuckDB data"
	@echo "  make replay-check  Verify the committed Fabric IQ replay artifact"
	@echo "  make clean         Remove local DuckDB and frontend build output"

# ---------------------------------------------------------------------------
# Start the application
# ---------------------------------------------------------------------------
setup:
	@command -v $(UV) >/dev/null 2>&1 || { echo "Missing required tool: uv (https://docs.astral.sh/uv/)"; exit 1; }
	@command -v $(PNPM) >/dev/null 2>&1 || { echo "Missing required tool: pnpm"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "Missing required tool: docker"; exit 1; }
	$(UV) sync --extra dev
	$(PNPM) --dir frontend install --frozen-lockfile
	docker compose up -d --wait postgres
	$(PYTHON) -m concord.storage.db
	$(PYTHON) -m concord.seed.seed_duckdb
	@echo "Setup complete. Start the app with: make dev"

postgres:
	docker compose up -d --wait postgres

seed:
	$(PYTHON) -m concord.seed.seed_duckdb

dev: postgres seed
	$(LAUNCH) --mode local

dev-fresh:
	@echo "dev-fresh resets ONLY local synthetic Concord IQ state (Postgres volume + DuckDB)."
	@echo "It never touches Azure, Fabric, Foundry, SharePoint, or committed replay artifacts."
	docker compose down -v
	docker compose up -d --wait postgres
	$(PYTHON) -m concord.storage.db
	$(PYTHON) -m concord.seed.seed_duckdb
	$(LAUNCH) --mode local --reset

dev-foundry: postgres seed
	$(LAUNCH) --mode foundry

dev-fabric: postgres seed
	$(LAUNCH) --mode fabric

dev-work-iq: postgres seed
	$(LAUNCH) --mode work-iq

stop:
	$(LAUNCH) --stop

frontend:
	$(PNPM) --dir frontend dev

demo: postgres seed
	$(PYTHON) -m concord.demo

scan: seed
	$(PYTHON) -m concord.scan

# ---------------------------------------------------------------------------
# Verify the project
# ---------------------------------------------------------------------------
test: test-backend test-frontend

test-backend:
	docker compose up -d --wait postgres
	$(PYTHON) -m pytest

test-frontend:
	$(PNPM) --dir frontend test

lint:
	$(PYTHON) -m ruff check backend tests
	$(PYTHON) -m ruff format --check backend tests
	$(PNPM) --dir frontend lint

eval: postgres seed
	$(PYTHON) -m concord.evals

judge-proof: postgres seed
	$(PYTHON) -m concord.judge_proof

# ---------------------------------------------------------------------------
# Cloud proofs
# ---------------------------------------------------------------------------
cloud-proof:
	$(PYTHON) -m concord.cloud_proof

semantic-pr-export: postgres seed
	$(PYTHON) -m concord.semantic_pr_export

work-iq-proof:
	$(PYTHON) -m concord.work_iq_proof

fabric-proof: replay-check

foundry-hosted-smoke:
	$(PYTHON) -m concord.ms_agent.foundry_hosted --smoke

# ---------------------------------------------------------------------------
# Lower-level cloud tooling (used by the proofs above)
# ---------------------------------------------------------------------------
agent-smoke: postgres seed
	CONCORD_SCENARIO_PACK=business PYTHONWARNINGS="ignore::FutureWarning" \
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
