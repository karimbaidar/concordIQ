# Getting started

Concord IQ supports a cloud-enabled presenter stack and a fully local fallback.
Repository defaults remain fail-closed: `PROVIDER=local`, `ALLOW_CLOUD=false`,
`MAX_CLOUD_CALLS=0`, LLM disabled.

## Prerequisites

- Docker Desktop with Docker Compose v2
- [`uv`](https://docs.astral.sh/uv/) for the Python 3.12 environment
- Node.js, `pnpm`, and GNU Make

## One-time setup

```bash
make setup
```

This is idempotent. It syncs the `.venv` with `uv`, installs the frontend with `pnpm`,
starts PostgreSQL, initializes the registry schema, seeds the deterministic DuckDB data,
and verifies required tooling. It never calls a cloud provider.

## Run the workbench

```bash
make dev
```

`make dev` is the reviewer command. It reads stable configuration from `.env`, acquires
short-lived Fabric and Foundry tokens in memory, and starts Learning with Fabric IQ Live
selected. The UI can switch to Fabric Replay, Foundry Agent Service Live, or Local.

```text
Concord IQ demo mode
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
Provider: fabric_iq + foundry_hosted + replay
Cloud:    enabled
```

For a credential-free stack:

```bash
make dev-local
```

Both commands stop their child processes cleanly on Ctrl+C. Use `make stop` for a stack
started in another shell.

## Reset the demo cold open

Canonical promotions persist. To record the unresolved three-way conflict from a clean
state:

```bash
make dev-fresh
```

This resets only local synthetic state (the PostgreSQL Docker volume and DuckDB),
reseeds, and verifies the Certification Ready conflict before starting local Learning.
It never touches Azure, Fabric, Foundry, SharePoint, or committed replay artifacts.

## Explore the rest of the system

```bash
make demo     # the three deterministic scenario verdicts
make scan     # portfolio scan, Concord Score, per-team leaderboard
make eval     # deterministic safety scorecard
make test     # backend + frontend tests
make lint     # ruff + frontend lint/typecheck
```

`make demo` prints:

```text
Active Customer: CONFLICT | counts=1600/1500/1334 | proposal drafted; human approval required
Net Revenue: CONSISTENT | counts=1600/1600 | decoy ruled out; no reconciliation needed
Churned Customer: CONFLICT | counts=333/666 | automatic reconciliation refused; human approval required
```

## Verified, credential-free Fabric IQ replay

```bash
make replay-check
```

This validates the committed sanitized Fabric IQ semantic-proof capture and replays the
full demo through `ReplayProvider` with cloud disabled — no Fabric tenant, token, or paid
capacity required.

For cloud modes, see [cloud runtime](cloud-runtime.md).
