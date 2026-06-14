# Threat model

## Assets

- synthetic analytical data and ontology definitions
- semantic authority rules
- executed SQL and evidence
- Microsoft access tokens or API keys during manual capture
- raw and sanitized provider responses

## Trust boundaries

```mermaid
flowchart LR
    USER["Reviewer"] --> UI["Certification Ready workbench"]
    UI --> WF1["Phase 1 Agent Framework workflow"]
    WF1 --> DB[("DuckDB SQL + PostgreSQL evidence")]
    WF1 -. "explicit opt-in only" .-> IQ["Fabric IQ semantic grounding"]
    IQ --> RAW["Ignored raw capture"]
    RAW --> REVIEW["Typed validation + human review"]
    REVIEW --> SAFE["Committed Certification Ready replay"]
    WF1 --> FROZEN["Frozen verifier-approved case"]
    FROZEN --> WF2["Phase 2 Semantic Court workflow"]
    WF2 -. "cannot mutate engine facts" .-> FROZEN
    WF1 -. "verified facts only" .-> MODEL["Optional narration model"]
    WF2 -. "verified facts only" .-> MODEL
    FROZEN --> OWNER["Learning Governance Council"]
    OWNER --> REG["Concord IQ registry only"]
```

## Primary risks and controls

| Risk | Control |
| --- | --- |
| Accidental paid cloud use | `ALLOW_CLOUD=false`, `MAX_CLOUD_CALLS=0`, guard before every request |
| Secret exposure | `.env` ignored, Pydantic secret types, no credential logging |
| Tenant information in git | raw directory ignored; sanitized artifact redacts URLs, emails, GUIDs |
| Confidential business data | synthetic datasets and scenarios only |
| Fabric/Foundry response drift | strict typed snapshot validation and fail-closed parsing |
| Prompt or tool injection | adapters request registered snapshots; deterministic verifier owns decisions |
| Generated narrative changes truth | text-only result type; typed decisions are finalized separately |
| Court changes the original verdict | Court receives a frozen case; `CourtAuditAgent` checks the engine truth digest |
| Court cites another run's evidence | citation set must exactly equal the frozen case evidence IDs |
| Duplicate reconciliation or proposal | Court endpoint uses the cached `run_id`; it performs no SQL rerun or proposal creation |
| Prompt injection through fact values | facts are JSON data; system prompt forbids instruction following |
| Ollama unavailable or malformed | deterministic fallback; reconciliation continues |
| Silent provider fallback | provider factory raises instead of substituting LocalProvider |
| Replay provenance confusion | verified capture flag required by default |
| Unsupported governance choice | reconciliation refuses when authority is missing or ambiguous |

## Public-repository review

Before staging a replay artifact:

1. Confirm the raw file remains ignored.
2. Inspect the sanitized JSON manually.
3. Search for tokens, keys, URLs, email addresses, tenant names, and GUIDs.
4. Confirm every scenario is marked synthetic.
5. Run the replay contract tests.
6. Review the diff before commit.

## Residual risks

Microsoft APIs, preview behavior, tool schemas, pricing, and tenant permissions can
change. The adapters require a current smoke test in the target tenant. Sanitizing
structured output reduces exposure but does not replace human review.
