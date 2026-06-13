# Certification Ready — Foundry Agent Service hosted smoke (planned strongest artifact)

> **Status: scaffolded, not yet captured.** This file reserves the home for the strongest
> planned IQ artifact — a hosted Foundry Agent Service invocation of the **learning**
> Certification Ready scenario. It has **not** been run yet, and nothing here is presented
> as a completed capture.

## What this will prove (once captured)

- Concord IQ deployed to Microsoft Foundry Agent Service under a clearly named deployment
  such as `concord-iq-certification-ready` (the existing Foundry project may be reused).
- The hosted `/responses` endpoint invoked for the **Certification Ready** term.
- The hosted agent returns the strict Concord IQ proof envelope
  (`verdict=conflict`, `verification_status=passed`, `specialist_steps=10`).
- `FoundryHostedProvider` accepts and validates that envelope.

## Honesty note

- The default reviewer mode runs locally with deterministic synthetic data and **no cloud
  calls**. This hosted smoke is an *optional* proof and is never a judging dependency.
- The hosted runtime uses `ReplayProvider` inside Foundry Agent Service for deterministic,
  reproducible evidence. **Fabric IQ does not compute the readiness counts** — they come only
  from executed SQL.
- The currently completed hosted capture is the business-pack
  [`foundry-agent-service-smoke.md`](foundry-agent-service-smoke.md). This learning capture is
  the planned upgrade once Azure access and a cloud budget are available in the build
  environment.

## How to capture it (only with Azure access + an explicit budget)

Read [`docs/foundry-agent-service.md`](../foundry-agent-service.md) first, including the
"Common deployment gotchas" section (module entrypoint, replay container env, root
`Dockerfile`, first-time `azd up`). Then, with credentials configured:

```bash
ALLOW_CLOUD=true MAX_CLOUD_CALLS=1 PROVIDER=foundry_hosted \
  CONCORD_SCENARIO_PACK=learning make foundry-hosted-smoke
```

Save the sanitized output here (UTC timestamp, repo commit, sanitized endpoint, envelope
JSON). Verify no tokens, Authorization headers, or tenant IDs are written.

## Local verification without Azure credentials

The Certification Ready governance behaviour is fully reproducible locally today:

```bash
make test            # includes the Certification Ready acceptance tests
make eval
make demo            # prints the three learning verdicts
```

A deterministic local Certification Ready semantic-PR proof is exported at
[`certification-ready-semantic-pr.md`](certification-ready-semantic-pr.md).
