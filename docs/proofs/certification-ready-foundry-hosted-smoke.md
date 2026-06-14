# Certification Ready — Foundry Agent Service hosted smoke

> **Status: verified live on June 13, 2026.** The existing `concord-iq-2` deployment,
> version 4, was invoked through Foundry Agent Service for the **Certification Ready**
> term.

## Sanitized result

```text
provider=replay
verdict=conflict
verification_status=passed
specialist_steps=10
```

This proves that Foundry Agent Service hosted the strict ten-stage Microsoft Agent
Framework reconciliation and returned a verifier-approved case through
`FoundryHostedProvider`.

## Honesty note

- The default reviewer mode can run locally with deterministic synthetic data and **no
  cloud calls**. This hosted smoke is an optional proof and is never a judging
  dependency.
- The hosted runtime uses `ReplayProvider` inside Foundry Agent Service for deterministic,
  reproducible evidence. **Fabric IQ does not compute the readiness counts** — they come only
  from executed SQL.
- The Semantic Court is a second, in-process Microsoft Agent Framework graph over the
  frozen hosted result. This proof does not claim that the Court itself is hosted on
  Foundry Agent Service.

## Re-run the smoke

Read [`docs/foundry-agent-service.md`](../foundry-agent-service.md) first, including the
"Common deployment gotchas" section (module entrypoint, replay container env, root
`Dockerfile`, first-time `azd up`). Then, with credentials configured:

```bash
ALLOW_CLOUD=true MAX_CLOUD_CALLS=1 PROVIDER=foundry_hosted \
  CONCORD_SCENARIO_PACK=learning make foundry-hosted-smoke
```

The command requires Azure access and an explicit one-call budget. It validates the
hosted envelope and must not write tokens, Authorization headers, tenant IDs, or tenant
URLs.

## Local verification without Azure credentials

The Certification Ready governance behaviour is fully reproducible locally today:

```bash
make test            # includes the Certification Ready acceptance tests
make eval
make demo            # prints the three learning verdicts
```

A deterministic local Certification Ready Semantic-PR proof is exported at
[`certification-ready-semantic-pr.md`](certification-ready-semantic-pr.md).
