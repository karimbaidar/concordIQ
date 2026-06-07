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

## Verified Fabric API surfaces (confirmed 2026-06)

The bootstrap and adapter REST/MCP surfaces were checked against current
Microsoft Learn (Ontology REST API pages updated 2026-05/06). They are verified,
not assumed:

| Surface | Endpoint | Status |
| --- | --- | --- |
| Create workspace | `POST /v1/workspaces` | Verified (GA) |
| Assign capacity | `POST /v1/workspaces/{id}/assignToCapacity` | Verified (GA) |
| Create lakehouse | `POST /v1/workspaces/{id}/lakehouses` | Verified (GA) |
| List items by type | `GET /v1/workspaces/{id}/items?type=Ontology` | Verified (`Ontology` is in the `ItemType` enum) |
| Create ontology | `POST /v1/workspaces/{id}/ontologies` (201 / 202 LRO) | Verified (preview) |
| Update definition | `POST /v1/workspaces/{id}/ontologies/{id}/updateDefinition?updateMetadata=true` | Verified (preview) |
| Definition payload | `{definition:{parts:[{path,payload,payloadType:"InlineBase64"}]}}` over `definition.json`, `EntityTypes/{id}/definition.json`, `.platform` | Verified shape |
| Ontology MCP endpoint | `/v1/mcp/dataPlane/workspaces/{ws}/items/{ont}/ontologyEndpoint` | Verified shape |

The only surface still treated as best-effort is the base64 `.platform`
definition part (its exact schema is not published). If `updateDefinition` is
rejected, the bootstrap preserves the created resources and prints the manual
Fabric UI import steps; nothing is lost.

## Prerequisites before cloud bootstrap

1. Enable the **"Enable Ontology item (preview)"** tenant setting in the Fabric
   admin portal. Creating an ontology fails without it.
2. The caller needs a **contributor** workspace role and the
   **`Item.ReadWrite.All`** delegated scope (user or service principal).
   `az account get-access-token --resource https://api.fabric.microsoft.com`
   supplies a suitable token for an authorized user.
3. The workspace must be on a **supported capacity. F2 is the minimum SKU** for
   the Ontology preview, so a planned F2 capacity is sufficient.

Official references:

- [Microsoft Agent Framework workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/)
- [Foundry hosted agents](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent)
- [Azure AI Search knowledge-base retrieval](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-retrieve)
- [Foundry IQ and agentic retrieval](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview)
- [Fabric IQ overview](https://learn.microsoft.com/en-us/fabric/iq/overview)
- [Fabric ontology MCP server](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-mcp-server)
- [Create Ontology (REST)](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology)
- [Update Ontology Definition (REST)](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/update-ontology-definition)
- [Ontology preview tenant settings](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview-tenant-settings)
- [Ontology billing and capacity usage](https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-capacity-usage)

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

## Fabric bootstrap

Concord IQ has one guarded workflow from deterministic local data to a verified
cloud replay:

```bash
make fabric-bootstrap-dry-run
ALLOW_CLOUD=true make fabric-bootstrap
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make capture
make replay-check
```

`make fabric-bootstrap-dry-run` makes no Microsoft call. It regenerates
`fabric_seed/` from `LocalProvider`, the fixed synthetic DuckDB seed, and the
typed replay schema. The package contains all three scenario snapshots, a
human-readable ontology seed, metric definitions, authority rules, and a
non-secret bootstrap report.

`make fabric-bootstrap` refuses unless `ALLOW_CLOUD=true`. It reads `.env`, uses
`FABRIC_IQ_ACCESS_TOKEN` or the current Azure CLI login, and creates or reuses the
configured Fabric workspace, lakehouse, and ontology through public APIs where
available. The command never writes `.env` and never prints the token. It prints
resource IDs and the ontology MCP endpoint for the operator to paste into `.env`.

Ontology definition import is a preview surface. If the import fails, Concord IQ
preserves the created resources, records the failure in
`fabric_seed/bootstrap-report.md`, and prints the manual Fabric UI steps. Upload
or paste the generated seed artifacts into the tiny lakehouse/ontology setup,
publish the ontology, and then run capture.

Fabric capture requires six budgeted MCP requests: initialize, initialized
notification, tool discovery, and one scenario request for Active Customer, Net
Revenue, and Churned Customer. `make replay-check` validates real-IQ provenance,
scenario completeness, ontology and definition evidence, executed evaluations,
authority rules, and secret hygiene. It then runs the demo with
`PROVIDER=replay`, `ALLOW_CLOUD=false`, and `MAX_CLOUD_CALLS=0`.

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
