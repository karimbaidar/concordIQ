# Certification Ready — Fabric IQ live capture (planned, sanitized home)

> **Status: scaffolded placeholder, not a capture.** This reserves the location for a
> sanitized Fabric IQ live capture of the **learning** Certification Ready concept grounding.
> It has not been run.

- The committed, verified sanitized Fabric IQ replay is [`latest.json`](latest.json) (business
  pack). It is the current honest artifact and backs the mandatory `make replay-check` gate.
- The planned strongest artifact is a single fresh Fabric IQ live capture for the **learning**
  ontology (Certification Ready concept grounding: learner, role, certification, required
  module, practice assessment, lab completion, manager approval, readiness rule), then
  **sanitized and saved as a replay artifact** alongside `latest.json`.
- **Fabric IQ grounds the concept; it does not compute the readiness counts.** The counts come
  only from executed SQL over synthetic learner data.

## How to capture it (only with Azure access + an explicit budget)

```bash
ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 CONCORD_SCENARIO_PACK=learning make fabric-mcp-diagnose
ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 CONCORD_SCENARIO_PACK=learning make capture
```

Sanitize the raw capture before committing it. Verify no tokens, Authorization headers, or
tenant IDs are present in the saved artifact.
