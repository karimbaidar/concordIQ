# Concord IQ — live cloud proof report

- **Generated (UTC):** 2026-06-11T23:19:23Z

| Integration | Status | Mode |
|---|---|---|
| Foundry Agent Service | SKIPPED | hosted_runtime |
| Fabric IQ (replay) | PASSED | sanitized_replay |
| Fabric IQ (live diagnostics) | SKIPPED | optional MCP diagnostics |
| Work IQ | LICENSE_GATED | optional_m365_artifact_grounding |

Cloud checks are honest: missing credentials or tenant entitlements are reported
as `skipped`/`license_gated`, never as success. No tokens, Authorization headers,
or tenant URLs appear in this report.
