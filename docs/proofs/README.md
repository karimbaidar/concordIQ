# Concord IQ proof index

| Proof | File | Meaning |
|---|---|---|
| One-command judge report | `judge-proof-report.md` | Summary of local and optional cloud verification. |
| Foundry Agent Service | `foundry-agent-service-smoke.md` | Real hosted `/responses` smoke proof (business pack). |
| Fabric IQ replay | `../../artifacts/replay/sanitized/latest.json` | Sanitized replay of verified Fabric IQ semantic grounding (business pack). |
| Work IQ status | `work-iq-license-gate.md` or `work-iq-artifact-proof.md` | M365 artifact grounding status. |
| Semantic PR export | `semantic-pr-export.md` | Governed definition-change artifact with hash (business pack). |
| Certification Ready semantic PR | `certification-ready-semantic-pr.md` | Deterministic local learning semantic-PR export (no cloud). |
| Certification Ready hosted smoke | `certification-ready-foundry-hosted-smoke.md` | Planned strongest artifact — scaffolded, not yet captured. |
| Certification Ready Fabric capture | `../../artifacts/replay/sanitized/certification-ready-capture.PLANNED.md` | Planned learning Fabric live capture — scaffolded home. |

Cloud checks are marked passed, skipped, or license-gated. Missing credentials or tenant entitlements are never hidden.

Regenerate everything in one command:

```bash
make judge-proof
```
