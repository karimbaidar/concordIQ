# Microsoft IQ integration

Concord IQ keeps provider identity visible because reproducibility and real IQ
integration are different claims.

## Provider modes

| Mode | Purpose | Network behavior |
| --- | --- | --- |
| `LocalProvider` | Deterministic development and reviewer mode | None |
| `ReplayProvider` | Rehearsal from a reviewed real-IQ capture | None |
| `FabricIQProvider` | Primary semantic grounding through ontology MCP | Guarded HTTPS/MCP |
| `FoundryIQProvider` | Fallback Azure AI Search knowledge-base retrieval | Guarded HTTPS |

When the Agent Framework tool receives `provider=auto`, it selects configured
Fabric IQ first. Foundry IQ is used only when Fabric IQ is unavailable. Explicit
provider names never fall back silently, and local mode remains the default.

The Foundry adapter calls the Azure AI Search knowledge-base `retrieve` action.
The default API version is `2026-04-01`, which uses semantic intents and returns
extractive grounding data. A configured knowledge source must contain Concord
IQ's synthetic scenario snapshot documents.

The Fabric adapter initializes the ontology MCP endpoint, lists tools, selects
`search_ontology` or `query_ontology`, and validates the returned snapshot.
Fabric tool schemas can evolve, so a tenant smoke test is required before this
adapter can be described as verified.

Official references:

- [Microsoft Agent Framework workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/)
- [Foundry hosted agents](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent)
- [Azure AI Search knowledge-base retrieval](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-retrieve)
- [Foundry IQ and agentic retrieval](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview)
- [Fabric IQ overview](https://learn.microsoft.com/en-us/fabric/iq/overview)
- [Fabric ontology MCP server](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-mcp-server)

## Configuration

Foundry IQ:

```text
PROVIDER=foundry_iq
ALLOW_CLOUD=true
MAX_CLOUD_CALLS=3
FOUNDRY_IQ_ENDPOINT=https://<search-service>.search.windows.net
FOUNDRY_IQ_KNOWLEDGE_BASE=<knowledge-base>
FOUNDRY_IQ_ACCESS_TOKEN=<short-lived-token>
```

Fabric IQ:

```text
PROVIDER=fabric_iq
ALLOW_CLOUD=true
MAX_CLOUD_CALLS=6
FABRIC_IQ_MCP_ENDPOINT=https://api.fabric.microsoft.com/v1/mcp/dataPlane/...
FABRIC_IQ_ACCESS_TOKEN=<short-lived-token>
```

Secrets are represented as Pydantic secret values and are never included in
provider status output, replay metadata, or logs.

## Foundry Agent Service

`concord.ms_agent.foundry_hosted_entrypoint` wraps the typed Microsoft Agent
Framework workflow in the optional Foundry responses host. It refuses to start
unless `ALLOW_CLOUD=true`, `MAX_CLOUD_CALLS` is positive, and Fabric IQ or Foundry
IQ configuration is present. See the
[integration README](../backend/concord/ms_agent/README.md) for environment
variables and smoke commands.

## What counts as real integration

The acceptance gate is:

1. A configured adapter successfully calls a real Microsoft IQ endpoint.
2. The response contains only synthetic Concord IQ scenario data.
3. The raw response is retained locally in the ignored raw directory.
4. A reviewed, secret-free sanitized artifact is committed.
5. `ReplayProvider` runs the same typed contract from that artifact.

This repository currently implements and tests both adapters with injected
transports, but no tenant was available for a real smoke test. Therefore no
sanitized capture is committed and the final IQ-integration gate remains open.
