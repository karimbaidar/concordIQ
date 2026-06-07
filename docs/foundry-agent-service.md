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

Current Microsoft references:

- [Foundry hosted agents](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent)
- [Hosted agents concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
