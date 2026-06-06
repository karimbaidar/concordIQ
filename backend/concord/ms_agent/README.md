# Microsoft Agent Framework integration

Concord IQ uses Microsoft Agent Framework as the application orchestration layer.
Ten typed workflow nodes coordinate a `ReconciliationCase`; the coordinator calls
the existing deterministic `ReconciliationRunner` through
`reconcile_business_term(term, period, provider)`.

## Local smoke test

Local mode is deterministic, uses synthetic data, and makes no Microsoft call:

```bash
make agent-smoke
```

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

## Foundry Agent Service scaffold

Install the optional preview hosting packages:

```bash
uv sync --extra dev --extra foundry-hosting
```

The entrypoint is:

```bash
python -m concord.ms_agent.foundry_hosted_entrypoint
```

Start with explicit configuration. Use placeholders only in documentation and
never commit real values:

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
and at least one real IQ provider is configured. A local deployment smoke command
is:

```bash
curl -sS http://127.0.0.1:8080/responses \
  -H 'content-type: application/json' \
  -d '{"input":"{\"term\":\"Active Customer\",\"provider\":\"auto\"}"}'
```

The exact Foundry deployment command and endpoint shape can change while hosted
agents are in preview; verify the current Microsoft documentation before a tenant
smoke test.

Do not assume Foundry, Fabric, or IQ usage is free or unlimited. Verify current
Microsoft pricing, trial limits, tenant settings, and permissions before enabling
cloud mode. Keep datasets tiny, use cloud only for smoke tests, pause or delete
idle resources, and replay sanitized captured responses through ReplayProvider
for demo rehearsal.
