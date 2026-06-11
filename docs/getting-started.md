# Getting started

Concord IQ runs fully locally with no cloud credentials. The default mode is safe:
`PROVIDER=local`, `ALLOW_CLOUD=false`, `MAX_CLOUD_CALLS=0`, LLM disabled.

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

`make dev` always starts safe local mode regardless of stale shell variables or `.env`
values. It prints the backend and frontend URLs and stops both child processes cleanly on
Ctrl+C. Use `make stop` to stop a stack started in another shell.

```text
Concord IQ local mode
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
Provider: local
Cloud:    disabled
```

## Reset the demo cold open

Canonical promotions persist. To record the unresolved three-way conflict from a clean
state:

```bash
make dev-fresh
```

This resets only local synthetic state (the PostgreSQL Docker volume and DuckDB),
reseeds, and verifies the Active Customer conflict (1600/1500/1334, $33.2M, approval
required) before starting. It never touches Azure, Fabric, Foundry, SharePoint, or
committed replay artifacts.

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
