# Cloud and cost controls

Concord IQ is local-first. Its default settings are:

```text
PROVIDER=local
ALLOW_CLOUD=false
MAX_CLOUD_CALLS=0
LLM_PROVIDER=disabled
```

Every Foundry IQ or Fabric IQ HTTP request checks both `ALLOW_CLOUD` and the
remaining `MAX_CLOUD_CALLS` budget before network I/O. The app does not probe
cloud endpoints from health checks, provider status, tests, or page load.

> Do not assume Foundry, Fabric, or IQ usage is free or unlimited. Verify current Microsoft pricing, trial limits, tenant settings, and permissions before enabling cloud mode. Keep datasets tiny, use cloud only for smoke tests, pause or delete idle resources, and replay sanitized captured responses through ReplayProvider for demo rehearsal.

## Fabric bootstrap, capture, and replay

Use a dedicated synthetic-only resource. First inspect the plan without network
access:

```bash
make fabric-bootstrap-dry-run
```

After verifying capacity, permissions, pricing, and preview API availability,
authenticate with a short-lived token or Azure CLI and opt in:

```bash
ALLOW_CLOUD=true make fabric-bootstrap
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make capture
make replay-check
```

Fabric capture uses initialization, initialized notification, and tool discovery
before the three scenario calls. The six-request budget is intentionally small.
Foundry IQ remains the fallback and uses one retrieve request per scenario:

```bash
PROVIDER=foundry_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=3 make capture
make replay-check
```

The command writes exact responses to `artifacts/replay/raw/`, which is ignored.
It then validates typed synthetic snapshots and writes a sanitized candidate to
`artifacts/replay/sanitized/latest.json`. Review that file before staging it.
`make replay-check` must pass before the artifact is presented as verified.

## Operational hygiene

- Use only the three small synthetic scenarios.
- Prefer Microsoft Entra ID tokens over long-lived keys.
- Never place tokens, endpoints with tenant identifiers, or raw responses in git.
- Pause or delete idle capacity and search resources.
- Rehearse with `ReplayProvider` after one verified smoke capture.
- Recheck current pricing and preview terms immediately before cloud use.

Current references:

- [Microsoft Fabric pricing](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/)
- [Microsoft Foundry pricing](https://azure.microsoft.com/en-us/pricing/details/microsoft-foundry/)
- [Fabric trial documentation](https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial)
