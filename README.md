# Concord IQ

**The false-readiness firewall for enterprise certification programs.**

Concord IQ is a multi-agent semantic reconciliation engine. It proves whether HR,
Learning & Development, and managers agree on what **Certification Ready** means
before an enterprise trusts readiness dashboards, spends exam budget, or reports
team readiness.

[![Hackathon](https://img.shields.io/badge/Microsoft_Agents_League_2026-Reasoning_Agents-5C2D91)](#challenge-alignment)
[![Challenge](https://img.shields.io/badge/Challenge_A-Enterprise_Learning_System-0078D4)](#challenge-alignment)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

## What it does

- Runs ten typed specialist stages through Microsoft Agent Framework.
- Executes competing definitions as deterministic SQL over fixed-seed synthetic data.
- Compares learner result sets; an LLM never decides the verdict.
- Shows false-ready learner IDs and synthetic exam-voucher spend at risk.
- Resolves authority from configured governance rules.
- Blocks unsupported cases through a skeptical verifier.
- Produces an evidence-backed Semantic PR that only the configured owner can approve.

## Challenge alignment

**Track:** Reasoning Agents
**Challenge A:** Enterprise Learning System

Most learning agents generate plans, quizzes, or recommendations. Concord IQ governs
the meaning behind the readiness signals those systems depend on. If teams define
readiness differently, every downstream score is unsafe.

The same engine also supports a secondary business-metrics scenario pack, demonstrating
that semantic reconciliation generalizes beyond learning.

## Demo scenario

The default learning pack proves three governance behaviours over the same synthetic
learner data — a real conflict, a rejected decoy, and a governed refusal.

### 1. Certification Ready — proven conflict

| Owner | Executed definition | Ready learners |
|---|---|---:|
| HR | All required modules complete | 80 |
| Learning & Development | Required modules complete and latest practice score >= 80% | 56 |
| Managers | Required labs complete and manager approval recorded | 56 |

The two 56-learner populations are not the same set. Concord IQ executes all three
definitions, proves the conflict, identifies **24 false-ready learners** in the HR claim,
and quantifies **$10,800 of synthetic exam-voucher spend at risk**. Authority is clear
(Learning Governance Council), so the engine drafts a Semantic PR that only that owner can
approve.

### 2. Required Training Complete — rejected decoy

Two differently-worded definitions — "all required modules completed" (HR) and "100%
required course completion" (Learning & Development) — execute to the **same 80 learners**.
Concord IQ rules the decoy out as wording-only: verdict `consistent`, low impact, **no
proposal and no refusal**.

### 3. Exam Eligible — governed refusal

Module-completion (HR, 80 learners) and lab-plus-manager-approval (Managers, 56 learners)
produce **materially different** sets, but enterprise authority over exam eligibility is
**ambiguous** — no configured owner can approve a canonical definition. Concord IQ refuses
automatic reconciliation, routes the decision to a human, and **promotes nothing**.

Every run includes the agent trace, exact SQL, evidence IDs, skeptical verification, the
resolved authority decision, and (for the conflict) a Semantic PR with owner-gated promotion
inside the Concord IQ registry.

[Screenshot placeholder: Certification Ready meaning fork and readiness outcome]

[Video placeholder: 2-3 minute Challenge A demo]

## Run locally

Prerequisites: Python 3.12+, `uv`, `pnpm`, Docker.

```bash
make setup
make dev
```

Open the frontend URL printed by `make dev` (normally
`http://127.0.0.1:5173`). No environment variable is required: missing
`CONCORD_SCENARIO_PACK` defaults to `learning`.

To reset local synthetic state before a recording:

```bash
make dev-fresh
```

Stop only the processes started by Concord IQ:

```bash
make stop
```

## Scenario packs

Learning is the challenge-facing default:

```bash
make dev
```

Run the preserved business-metrics pack:

```bash
CONCORD_SCENARIO_PACK=business make dev
```

Valid values are `learning` and `business`. Invalid values fail with an actionable
configuration error.

## Microsoft IQ usage

**Default reviewer mode runs locally with deterministic synthetic data and no cloud calls.
Fabric IQ and Foundry Agent Service proofs are included as sanitized replay captures.**

The IQ integration applies to the **learning** default. Fabric IQ grounds the governed
**Certification Ready** concept and its semantic graph — learner, role, certification,
required module, practice assessment, lab completion, manager approval, and the readiness
rule. Concord IQ's deterministic engine then executes and verifies the competing definitions
against synthetic learner data. **Fabric IQ does not compute the readiness counts**; the
counts come only from executed SQL.

- **Microsoft Agent Framework:** implemented ten-stage typed workflow used by both packs.
- **Foundry Agent Service:** a real hosted deployment and invocation are recorded as a
  sanitized capture in
  [`docs/proofs/foundry-agent-service-smoke.md`](docs/proofs/foundry-agent-service-smoke.md).
- **Fabric IQ:** semantic grounding is proven through a verified, sanitized replay capture.
  The committed live/replay capture is currently anchored to the business pack; a learning
  **Certification Ready** live capture is the planned strongest artifact and is scaffolded in
  [`docs/proofs/`](docs/proofs/) and [`artifacts/replay/sanitized/`](artifacts/replay/sanitized/).
- **Foundry IQ:** advisory authority grounding is transport-tested; no real-tenant Foundry IQ
  capture is claimed.
- **Work IQ:** the guarded adapter is implemented, but live retrieval is license-gated in the
  available tenant — never reported as a live retrieval.

The Certification Ready scenario uses deterministic local synthetic data. It is
representative of enterprise learning artifacts and is **not** presented as a live Work
IQ retrieval.

## Tests

Run the complete reproducible judge gate:

```bash
make judge-proof
```

Or run the main gates separately:

```bash
make test
make lint
```

`make judge-proof` keeps the established Fabric replay, eval scorecard, and
content-hashed Active Customer Semantic-PR proof anchored to the business pack while
the full backend/frontend suites cover the learning default.

## Safety and reliability

- Deterministic SQL result-set equality owns conflict versus consistency.
- Configured rules own authority decisions.
- The skeptical verifier blocks unsupported or incomplete cases.
- Ambiguous authority causes refusal, never an invented owner.
- Canonical promotion requires the configured human authority owner.
- Cloud access is disabled by default and fails closed without permission and budget.
- All local demo data is synthetic, fixed-seed, and dated to a fixed reference date.
- Canonical promotion changes only the Concord IQ registry; it does not write back to
  Fabric IQ, Foundry IQ, or Work IQ.

## License

Apache License 2.0. See [LICENSE](LICENSE).
