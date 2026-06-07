# Microsoft Agent Framework integration

Concord IQ uses Microsoft Agent Framework as the application orchestration layer.
Ten typed workflow nodes coordinate a `ReconciliationCase` in two modes:

- `fast` is the stable default. The coordinator calls the complete deterministic
  `ReconciliationRunner`, and each specialist validates its typed stage output.
- `strict` lets Agent Framework own progression. The coordinator creates the case
  and plan, then every specialist invokes exactly one deterministic runner stage
  before passing the typed casefile onward.

Both modes use the same SQL execution, evidence, authority, reconciliation,
verifier, and audit methods. Optional narration cannot change their decisions.

## Local smoke test

Local mode is deterministic, uses synthetic data, and makes no Microsoft call:

```bash
make agent-smoke
CONCORD_WORKFLOW_MODE=strict make agent-smoke
```

The command prints `workflow=fast` or `workflow=strict`. Strict mode never invokes
the runner's complete `run()` path.

Strict verification checks deterministic evidence IDs, exact SQL, result-set
equality or divergence, authority, and proposal/refusal consistency. It may
recompute one wholly missing stage output once from the configured provider.
Partial or contradictory evidence is never patched: the case returns `blocked`,
or `needs_review` when the single recovery attempt still fails, and is not
persisted as complete.

The period format is `YYYY-MM-DD/YYYY-MM-DD`. Hosted messages may be a plain term
or a JSON object:

```json
{
  "term": "Active Customer",
  "period": "2026-03-04/2026-06-01",
  "provider": "auto"
}
```

## Provider priority

- `auto` first selects `FabricIQProvider` when its endpoint and token exist.
- `FoundryIQProvider` is selected only when Fabric IQ is unavailable and the
  Foundry IQ knowledge base is configured.
- `local` selects `LocalProvider` explicitly for reproducible development and
  public review. It is not a simulated Microsoft IQ service.
- `replay` selects a reviewed sanitized capture without making a cloud call.

No cloud provider silently falls back to local data.

## Fabric grounding workflow

Prepare and inspect the deterministic seed package without cloud access:

```bash
make fabric-bootstrap-dry-run
```

After current pricing, tenant permissions, and preview API availability are
verified, bootstrap the tiny Fabric resources and capture the three scenarios:

```bash
ALLOW_CLOUD=true make fabric-bootstrap
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make capture
make replay-check
```

The bootstrap never writes `.env` or prints access tokens. Fabric capture needs
six requests because MCP initialization and tool discovery precede the three
scenario calls. A sanitized artifact is not considered verified until
`make replay-check` passes and runs the cloud-free replay demo.

## Foundry Agent Service scaffold

Install the optional preview hosting packages:

```bash
uv sync --extra dev --extra foundry-hosting
```

Validate the real hosting adapter without cloud access or Fabric credentials:

```bash
make foundry-agent-dry-run
make foundry-agent-smoke
```

The dry-run constructs `ResponsesHostServer` and verifies its protocol routes.
The smoke sends Active Customer through `/responses` in strict workflow mode,
requires all ten specialist steps, and checks deterministic verifier approval.
Set `FOUNDRY_AGENT_PROVIDER=replay` to exercise a verified sanitized capture.

See [`docs/foundry-agent-service.md`](../../../docs/foundry-agent-service.md) for
the full local protocol and deployment guide.

For a real hosted process, start with explicit configuration. Use placeholders
only in documentation and never commit real values:

```text
ALLOW_CLOUD=true
MAX_CLOUD_CALLS=3
FOUNDRY_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<deployment-name>
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<database>
DUCKDB_PATH=/data/concord_iq.duckdb

# Primary semantic grounding
FABRIC_IQ_MCP_ENDPOINT=https://api.fabric.microsoft.com/v1/mcp/dataPlane/...
FABRIC_IQ_ACCESS_TOKEN=<short-lived-token>

# Fallback semantic grounding
FOUNDRY_IQ_ENDPOINT=https://<search-service>.search.windows.net
FOUNDRY_IQ_KNOWLEDGE_BASE=<knowledge-base>
FOUNDRY_IQ_ACCESS_TOKEN=<short-lived-token>
```

`FOUNDRY_PROJECT_ENDPOINT` and `AZURE_AI_MODEL_DEPLOYMENT_NAME` are deployment
settings used by Foundry tooling when a model-backed hosted surface is attached.
The deterministic Concord IQ workflow itself does not require a model call.

The host fails closed unless `ALLOW_CLOUD=true`, `MAX_CLOUD_CALLS` is positive,
and at least one real IQ provider is configured. Then run:

```bash
python -m concord.ms_agent.foundry_hosted_entrypoint
```

The exact Foundry deployment command and endpoint shape can change while hosted
agents are in preview; verify the current Microsoft documentation before a tenant
smoke test.

Do not assume Foundry, Fabric, or IQ usage is free or unlimited. Verify current
Microsoft pricing, trial limits, tenant settings, and permissions before enabling
cloud mode. Keep datasets tiny, use cloud only for smoke tests, pause or delete
idle resources, and replay sanitized captured responses through ReplayProvider
for demo rehearsal.
