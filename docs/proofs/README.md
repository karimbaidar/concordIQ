# Concord IQ proof index

| Proof | File | Meaning |
|---|---|---|
| One-command judge report | `judge-proof-report.md` | Summary of local and optional cloud verification. |
| Foundry Agent Service | `foundry-agent-service-smoke.md` | Real hosted `/responses` smoke proof. |
| Fabric IQ replay | `../../artifacts/replay/sanitized/latest.json` | Sanitized replay of verified Fabric IQ semantic grounding. |
| Work IQ status | `work-iq-license-gate.md` or `work-iq-artifact-proof.md` | M365 artifact grounding status. |
| Semantic PR export | `semantic-pr-export.md` | Governed definition-change artifact with hash. |

Cloud checks are marked passed, skipped, or license-gated. Missing credentials or tenant entitlements are never hidden.

Regenerate everything in one command:

```bash
make judge-proof
```
