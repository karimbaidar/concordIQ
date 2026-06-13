# Concord IQ — judge proof report

- **Generated (UTC):** 2026-06-13T19:46:37Z
- **Git commit:** `7be62571e8b5422a0810226014b1497dfac182e6`
- **Mandatory local proof:** ✅ PASSED

## Local verification (mandatory)

| Check | Status | Detail |
|---|---|---|
| Local tests (backend) | ✅ PASSED |  |
| Frontend tests | ✅ PASSED |  |
| Lint / typecheck | ✅ PASSED |  |
| Eval scorecard | ✅ PASSED |  |
| Replay proof | ✅ PASSED |  |
| Semantic PR export | ✅ PASSED |  |

## Optional cloud integrations

| Integration | Status | Mode |
|---|---|---|
| Foundry Agent Service | ⏭️ SKIPPED | hosted_runtime |
| Fabric IQ (replay) | ✅ PASSED | sanitized_replay |
| Fabric IQ (live diagnostics) | ⏭️ SKIPPED | optional MCP diagnostics |
| Work IQ | 🔒 LICENSE-GATED | optional_m365_artifact_grounding |

Fabric IQ semantic grounding is reproduced through sanitized replay proof.

## Commands a judge can run

```bash
make judge-proof          # this report
make test                 # backend + frontend tests
make lint                 # ruff + frontend lint
make eval                 # deterministic safety scorecard
make replay-check         # verified Fabric IQ replay artifact
make semantic-pr-export   # governed definition-change artifact + hash
```

Optional cloud (only run with credentials and `ALLOW_CLOUD=true`):

```bash
ALLOW_CLOUD=true MAX_CLOUD_CALLS=1 PROVIDER=foundry_hosted make foundry-hosted-smoke
ALLOW_CLOUD=true MAX_CLOUD_CALLS=3 PROVIDER=work_iq make work-iq-proof
```

## Honesty note

Cloud checks are marked `passed`, `skipped`, `license_gated`, or `permission_blocked`.
Missing credentials or tenant entitlements are never hidden and never reported as
success. Work IQ is only `passed` when a live Microsoft Graph retrieval returns at
least one hit; until the tenant is entitled for the Retrieval API it stays
`license_gated`. No tokens, Authorization headers, or tenant URLs appear in this report.

- Machine-readable copy: `artifacts/proof/latest.json`
- Proof index: `docs/proofs/README.md`
