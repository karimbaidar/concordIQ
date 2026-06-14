# Concord IQ proof index

| Proof | File | Meaning |
|---|---|---|
| One-command judge report | `judge-proof-report.md` | Summary of local and optional cloud verification. |
| Foundry Agent Service | `foundry-agent-service-smoke.md` | Real hosted `/responses` smoke proof (business pack). |
| Fabric IQ replay | `../../artifacts/replay/sanitized/latest.json` | Sanitized replay of verified Fabric IQ semantic grounding (business pack). |
| Certification Ready Fabric replay | `../../artifacts/replay/sanitized/certification-ready.latest.json` | Sanitized verified Fabric grounding for the 120-learner workbench case; deterministic execution produces 80/56/56. |
| Certification Ready scale package | `../../fabric_seed/learning_cli/ciq_certification_ready_summary.json` | Separate 10,000-row Fabric-bound artifact: 522 canonical-ready and 4,334 false-ready. It is not the 120-learner workbench execution. |
| Work IQ status | `work-iq-license-gate.md` or `work-iq-artifact-proof.md` | M365 artifact grounding status. |
| Semantic PR export | `semantic-pr-export.md` | Governed definition-change artifact with hash (business pack). |
| Certification Ready semantic PR | `certification-ready-semantic-pr.md` | Deterministic local learning semantic-PR export (no cloud). |
| Certification Ready hosted smoke | `certification-ready-foundry-hosted-smoke.md` | Real Foundry Agent Service invocation of the ten-stage workflow over the verified learning replay. The second Court graph is not claimed as hosted. |
| Semantic Court capture | `../../artifacts/replay/sanitized/certification-ready.deliberation.json` | Digest-sealed second Agent Framework workflow over one frozen Certification Ready run. |

Cloud checks are marked passed, skipped, or license-gated. Missing credentials or tenant entitlements are never hidden.

Regenerate everything in one command:

```bash
make judge-proof
```
