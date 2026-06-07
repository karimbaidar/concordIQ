# Foundry Agent Service

Concord IQ can expose its Microsoft Agent Framework workflow through the
Foundry Responses hosting protocol. The hosted surface remains a thin deployment
layer: specialist agents still call the deterministic reconciliation runner,
which owns SQL execution, evidence, authority, verification, and persistence.

## Cloud-free validation

Install and validate the optional preview host without opening a socket, touching
Microsoft services, or requiring Fabric credentials:

```bash
make foundry-agent-dry-run
```

The command forces `PROVIDER=local`, `ALLOW_CLOUD=false`, and
`MAX_CLOUD_CALLS=0`. It constructs the Agent Framework workflow, wraps it in
`ResponsesHostServer`, and verifies the `/readiness` and `/responses` routes.

Exercise the complete OpenAI-compatible Responses request path in process:

```bash
make foundry-agent-smoke
```

The default smoke uses LocalProvider, strict workflow mode, synthetic DuckDB
data, PostgreSQL persistence, all ten specialist steps, and no cloud call.
The command validates HTTP readiness, parses the returned typed casefile, and
requires deterministic verification to pass.

To exercise a reviewed sanitized replay artifact instead:

```bash
FOUNDRY_AGENT_PROVIDER=replay make foundry-agent-smoke
```

Replay mode requires the configured artifact to satisfy the existing verified
capture gate. It does not contact Fabric or Foundry.

## Why the host is stateless

Each Concord IQ request creates an independent reconciliation casefile. The
host therefore builds a fresh Agent Framework workflow for every Responses
request. This avoids storing application-specific Python casefile objects in
preview host checkpoints while preserving the complete typed specialist flow.
PostgreSQL remains the durable audit and evidence store.

## Real hosted mode

Running the module without `--dry-run` or `--smoke` defaults to provider `auto`.
That path fails closed unless cloud access, a positive request budget, and a
real IQ provider are configured:

```bash
PROVIDER=auto \
ALLOW_CLOUD=true \
MAX_CLOUD_CALLS=3 \
uv run --extra dev --extra foundry-hosting \
  python -m concord.ms_agent.foundry_hosted_entrypoint
```

`auto` prefers Fabric IQ and uses Foundry IQ only as fallback. Local and replay
are explicit reviewer modes; neither is represented as Microsoft IQ.

The local server follows the Responses protocol:

```bash
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input":"{\"term\":\"Active Customer\"}"}'
```

Foundry deployment tooling may inject `FOUNDRY_PROJECT_ENDPOINT`,
`AZURE_AI_MODEL_DEPLOYMENT_NAME`, and telemetry settings. Concord IQ's
deterministic workflow does not require a model deployment to make its verdict,
but tenant deployment and identity setup must follow the current preview
documentation.

## Safety and status

- No secrets or tenant identifiers belong in source control.
- The dry-run and smoke commands explicitly disable cloud calls.
- Real hosting does not silently fall back to LocalProvider.
- This repository validates the hosting protocol locally; it does not claim a
  successful tenant deployment.

Do not assume Foundry, Fabric, or IQ usage is free or unlimited. Verify current
Microsoft pricing, trial limits, tenant settings, and permissions before enabling
cloud mode. Keep datasets tiny, use cloud only for smoke tests, pause or delete
idle resources, and replay sanitized captured responses through ReplayProvider
for demo rehearsal.

## Hosted deployment runbook (real cloud runtime)

Foundry Agent Service is the intended cloud runtime. The hosted agent runs over
**ReplayProvider**, so it needs no Fabric credentials or capacity — the committed
verified Fabric IQ replay artifact carries the grounding. Deployment automation
depends on tenant-specific preview APIs, so this is a manual runbook; the smoke
runs against an already-deployed endpoint. Do not fake a deployment.

1. **Prepare locally (no cloud).**
   ```bash
   make foundry-hosted-dry-run     # checks the entrypoint + committed replay artifact
   make foundry-hosted-package      # writes artifacts/foundry/package-report.md
   ```
2. **Create or select a Microsoft Foundry project** in the Foundry portal.
3. **Deploy Concord IQ as a hosted/containerized agent** using the existing
   entrypoint as the start command:
   ```bash
   python -m concord.ms_agent.foundry_hosted_entrypoint
   ```
   Install the app with the `foundry-hosting` extra. Ship the application package,
   `pyproject.toml`/`uv.lock`, `ontology/`, `data/synthetic/`, and the committed
   `artifacts/replay/sanitized/latest.json`. **Never** ship `.env`, tokens,
   `.venv/`, `node_modules/`, `artifacts/replay/raw/`, diagnostics, planning files,
   or screenshots.
4. **Configure the hosted environment** (inside the deployed app):
   ```text
   PROVIDER=replay
   AGENT_WORKFLOW_MODE=strict
   ALLOW_CLOUD=false
   MAX_CLOUD_CALLS=0
   REPLAY_ARTIFACT_PATH=artifacts/replay/sanitized/latest.json
   ```
5. **Configure the local smoke caller** (your machine, reaching the deployed agent):
   ```text
   ALLOW_CLOUD=true
   MAX_CLOUD_CALLS=1
   FOUNDRY_HOSTED_ENDPOINT=https://<your-deployed-agent>
   FOUNDRY_ACCESS_TOKEN=<short-lived bearer token>
   ```
6. **Run the real cloud smoke** (one call):
   ```bash
   ALLOW_CLOUD=true MAX_CLOUD_CALLS=1 make foundry-hosted-smoke
   ```
   It sends *"Why do our Active Customer dashboards disagree?"*, then asserts the
   response proves `provider_mode=replay`, `workflow_mode=strict`,
   `term=Active Customer`, `verdict=conflict`, `verification_status=passed`,
   `specialist_steps=10`, and writes `artifacts/foundry/hosted-smoke-report.md`
   (no token). Only after this passes may docs say
   **"Foundry Agent Service cloud runtime smoke verified."**
7. **Delete or stop the hosted resources** afterward to avoid charges.

## Current Microsoft references

- [Foundry hosted agents](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent)
- [Hosted agents concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
