# Semantic PR export — Certification Ready

> Governed definition-change artifact. Generated deterministically from executed SQL;
> contains no secrets and no tenant data.

- **Term:** Certification Ready
- **Verdict:** `conflict`
- **SHA-256:** `29aa293b7132ddbf240d384e4a1bab478c15ea6946dc2cafa8192cc5658c9e36`
- **Timestamp (UTC):** 2026-06-13T12:19:07Z
- **Machine-readable artifact:** `artifacts/semantic-pr/latest.json`

## Conflicting definitions

| Team | Definition | Count |
|---|---|---:|
| HR | Learner has completed every required learning module for the certification. | 80 |
| Learning & Development | Learner has completed every required module and the latest practice assessment score is at least 80 percent. | 56 |
| Managers | Learner has completed every required lab and has a recorded manager approval. | 56 |

## Proposed canonical definition

Certification Ready means a learner has completed every required learning module and scored at least 80 percent on the latest practice assessment. Manager readiness remains a named operational view until the Learning Governance Council approves a broader composition.

- **Source definition:** `certification_ready_learning`
- **Rationale:** HR marks 24 learners ready who do not meet the Learning and Development practice threshold, exposing 10,800.00 in synthetic exam-voucher spend. Learning Governance Council governs the enterprise readiness term.
- **Expected dashboard impact:** 24 false-ready learners and 10,800.00 in synthetic exam spend are exposed.

## Governance

- **Owner / approver:** Learning Governance Council
- **Authority status:** `clear`
- **Requires human approval:** True

## SQL / verifier result

- **Verdict:** `conflict`
- **Verification status:** `passed`
- **Deterministic checks passed:** 18/18

## Evidence IDs

- `24549b37-368e-56cc-aca5-89674c006bec`
- `7e9228d3-ac2d-5967-ba9f-b015796f2b8b`
- `36a4228c-cc18-5b95-ba97-f3239a2bf528`

The canonical proposal is exported with `requires_human_approval=true`. Concord IQ
never merges a canonical definition without the configured governance owner.
