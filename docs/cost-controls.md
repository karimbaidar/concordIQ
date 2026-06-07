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

## Fabric F2 budget runbook (target: well under EUR 100)

The captured IQ run is a few minutes of work; the only thing that spends real
money is leaving an F-capacity *running*. Treat capacity time as the budget.

1. **Use the minimum SKU.** F2 is the minimum capacity that supports the Ontology
   preview, so provision **F2** — not a larger SKU. (Confirm the current F2
   hourly rate on the Fabric pricing page before you start; do not assume it.)
2. **Pause when idle, always.** Fabric capacities can be paused and resumed, and
   pausing stops compute billing. Resume only for the minutes you bootstrap and
   capture, then pause again immediately. This is the single most important
   control.
3. **Disable graph auto-refresh.** The ontology's child Graph item can be set to
   refresh on a schedule and that consumes capacity. Leave it manual/disabled for
   a one-off capture.
4. **Keep the workload tiny.** Only the three synthetic scenarios are captured
   (six budgeted MCP calls). Ontology Modeling bills ~0.0039 CU/hr per definition
   in 30-minute windows, and NL2Ontology reasoning is token-metered and smoothed
   over 24 hours — both are negligible at this scale.
5. **Monitor.** Install the Microsoft Fabric Capacity Metrics app to watch actual
   CU usage while the capacity is live.
6. **Delete when done.** After the sanitized artifact passes `make replay-check`,
   delete the workspace and (if it was created only for this) the capacity. From
   then on the demo runs entirely on `ReplayProvider` at zero cost.

Minimal-cost path end to end:

```bash
# 1. (Fabric portal) resume the F2 capacity; ensure "Enable Ontology item (preview)"
make fabric-bootstrap-dry-run                                  # EUR 0, no cloud
ALLOW_CLOUD=true make fabric-bootstrap                         # create resources
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make capture
make replay-check                                             # validate + replay
# 2. (Fabric portal) PAUSE or DELETE the F2 capacity
```

See [iq-integration.md](iq-integration.md) for the verified API surfaces and the
tenant/role/capacity prerequisites.

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
