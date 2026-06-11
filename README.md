# Concord IQ

**Version control for business meaning.** Concord IQ detects when teams use the same
metric name differently, executes every definition against data, quantifies the impact,
and turns the resolution into an authority-gated semantic pull request.

[![Hackathon](https://img.shields.io/badge/Hackathon-Microsoft_Agents_League_2026-5C2D91)](#7-microsoft-integration-truth-table)
[![Track](https://img.shields.io/badge/Track-Reasoning_Agents-0078D4)](#7-microsoft-integration-truth-table)
[![IQ architecture](https://img.shields.io/badge/IQ-Fabric_%2F_Foundry_%2F_Work-00A4EF)](#7-microsoft-integration-truth-table)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

## 1. The problem, in one concrete example

> Finance reports **1,600** Active Customers. Sales reports **1,500**. Customer Success
> reports **1,334**. Concord IQ executes all three definitions, proves the **$33.2M**
> disagreement, and creates an authority-gated semantic pull request.

| Team | Definition | Count |
|---|---|---:|
| Finance | Recognized revenue in the trailing 90 days | 1,600 |
| Sales | Open or won opportunity in the trailing 180 days | 1,500 |
| Customer Success | Active contract + qualifying usage in the trailing 30 days | 1,334 |

A naming match does not prove operational equivalence. A wording difference does not
prove a real data conflict. Concord IQ settles both with executed SQL.

![Concord IQ meaning fork showing three Active Customer definitions and their proven impact](docs/assets/meaning-fork.svg)

## 2. 60-second quickstart

```bash
git clone <repo>
cd concord-iq
make setup
make dev
```

Then:

1. Open the frontend URL printed by `make dev` (`http://127.0.0.1:5173`).
2. Select **Active Customer**.
3. Click **Analyze disagreement**.

`make help` prints the full command table at any time.

## 3. One-command judge verification

```bash
make judge-proof
```

This runs the mandatory local proof — backend + frontend tests, lint/typecheck, the
deterministic eval scorecard, replay verification, the signed semantic-PR export, and a
local demo smoke — then reports optional cloud evidence honestly. It fails only when a
mandatory local check fails; missing cloud credentials are reported as `skipped`, never
as success. Output lands in [`docs/proofs/judge-proof-report.md`](docs/proofs/judge-proof-report.md)
and [`artifacts/proof/latest.json`](artifacts/proof/latest.json).

## 4. Demo modes

| Command | Purpose |
|---|---|
| `make dev` | Safe local UI — cloud disabled, always local |
| `make dev-fresh` | Reset synthetic demo state and start the cold-open UI |
| `make dev-foundry` | Foundry-hosted UI with an automatically acquired token |
| `make dev-fabric` | Live Fabric IQ mode with an automatically acquired token |
| `make dev-work-iq` | Work IQ mode with MSAL device-code authentication |
| `make judge-proof` | Reproducible mandatory judge proof |
| `make cloud-proof` | All configured live cloud proofs |
| `make stop` | Stop only the Concord IQ dev processes |

`make dev` always forces safe local mode (`PROVIDER=local`, `ALLOW_CLOUD=false`,
`MAX_CLOUD_CALLS=0`, strict workflow) and strips any inherited cloud tokens, so a stale
shell or `.env` can never silently invoke a cloud provider. The cloud modes acquire a
short-lived token at runtime — you never paste a bearer token. See
[cloud runtime](docs/cloud-runtime.md).

`make dev-fresh` resets **only** local synthetic Concord IQ state (the PostgreSQL Docker
volume and DuckDB), reseeds, and verifies the unresolved three-way conflict before
starting — so a recording always opens cold. It never touches Azure, Fabric, Foundry,
SharePoint, or committed replay artifacts.

## 5. How Concord IQ works

![Concord IQ architecture: experience, API and runtime, agent orchestration, grounding/data/governance, and governed outcomes](https://gist.githubusercontent.com/karimbaidar/13c0b4f161f4e894afcc39f6e3afbd5f/raw/architecture.png)

> Semantic grounding informs. Deterministic execution proves. Governance authorizes.
> Humans approve. LLMs explain, but do not decide.

Deterministic SQL owns the verdict. Configured governance owns authority. The Microsoft
Agent Framework coordinates ten specialist nodes through a typed casefile; the LLM is
optional narration that can never change a verdict, authority decision, or refusal. The
skeptical verifier blocks unsupported cases, and ambiguous authority causes a refusal,
not a guess.

```text
CoordinatorAgent -> ConceptResolverAgent -> BindingInspectorAgent
-> ConflictHypothesisAgent -> DataExecutionAgent -> ImpactRankerAgent
-> AuthorityResolverAgent -> ReconciliationAgent
-> SkepticalVerifierAgent -> AuditAgent
```

The reviewer workbench leads with the meaning-fork visual: real executed counts diverge,
the deterministic what-if control moves the dollar impact live, authority refusal leaves
the fork unresolved, and an approved canonical collapses it into one governed node. More
detail lives in [architecture](docs/architecture.md) and
[IQ integration](docs/iq-integration.md).

## 6. Getting started in depth

Prerequisites and the full local workflow (seed, scan, score, replay) are in
[getting started](docs/getting-started.md). The recordable narrative is in
[demo script](docs/demo-script.md).

## 7. Microsoft integration truth table

| Capability | Role | Proof status |
|---|---|---|
| Microsoft Agent Framework | 10-step specialist workflow | Implemented and tested |
| Foundry Agent Service | Hosted runtime | Real deployment/invocation recorded |
| Fabric IQ | Semantic grounding | Verified sanitized capture + replay |
| Foundry IQ | Advisory authority grounding | Integrated and transport-tested; no real-tenant capture |
| Work IQ | M365 artifact grounding | Implemented and permission-tested; live retrieval currently license-gated |
| Deterministic SQL | Verdict engine | Local/replay verified |
| Skeptical verifier | Blocking safety gate | Deterministic tests and evals pass |

These are distinct facts and are never collapsed into a single "Microsoft IQ passed"
claim. Work IQ is reported as `passed` only when a live Microsoft Graph retrieval returns
at least one hit; until the tenant is entitled it stays `license_gated`.

## 8. Proof bundle

- [`docs/proofs/README.md`](docs/proofs/README.md) — proof index
- [`docs/proofs/judge-proof-report.md`](docs/proofs/judge-proof-report.md) — mandatory local proof
- [`docs/proofs/foundry-agent-service-smoke.md`](docs/proofs/foundry-agent-service-smoke.md) — recorded hosted invocation
- [`docs/proofs/work-iq-license-gate.md`](docs/proofs/work-iq-license-gate.md) — honest Work IQ status
- [`artifacts/replay/sanitized/latest.json`](artifacts/replay/sanitized/latest.json) — verified Fabric IQ replay capture
- [`docs/eval-scorecard.md`](docs/eval-scorecard.md) — deterministic safety scorecard

Run the optional live cloud proofs with one command:

```bash
make cloud-proof
```

## 9. Repository map

```text
backend/concord/
  agents/          deterministic specialist agents
  analytics/       DuckDB execution utilities
  api/             FastAPI reconciliation and demo routes
  cloud_auth.py    runtime token acquisition (Azure CLI + MSAL)
  dev_launcher.py  safe local / cloud dev-stack launcher
  evals/           deterministic safety scorecard
  llm/             disabled/local narration providers
  ms_agent/        Microsoft Agent Framework workflow + Foundry host
  orchestration/   casefile and typed state machine
  providers/       Local, Replay, Fabric IQ, Foundry IQ, Work IQ, Foundry hosted
  seed/            fixed-seed synthetic generator
  storage/         SQLAlchemy registry models
frontend/          React/Vite reviewer workbench
docs/              architecture, getting started, cloud runtime, proofs, demo
artifacts/replay/  raw (ignored) and sanitized (committed) captures
tests/             deterministic acceptance tests
```

## 10. License

Concord IQ is licensed under the [Apache License 2.0](LICENSE), including its explicit
patent grant.
