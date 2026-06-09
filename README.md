# Concord IQ

**The semantic reconciliation agent for enterprise meaning.**

[![Hackathon](https://img.shields.io/badge/Hackathon-Microsoft_Agents_League_2026-5C2D91)](#hackathon-alignment)
[![Track](https://img.shields.io/badge/Track-Reasoning_Agents-0078D4)](#hackathon-alignment)
[![IQ architecture](https://img.shields.io/badge/IQ-Fabric_IQ_%2F_Foundry_IQ-00A4EF)](#microsoft-iq-architecture)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Agent_Framework_ready-0078D4)](#implementation-status)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

![Concord IQ meaning fork showing three Active Customer definitions and their proven impact](docs/assets/meaning-fork.svg)

> Enterprises built a single source of truth for data, but not for meaning.

Finance, Sales, and Customer Success can use the same business term while binding
it to different filters, time windows, populations, grains, and sources. Concord IQ
is designed to find those differences, execute each definition against data, rank
the material impact, and propose a governed semantic reconciliation. When authority
is shared or ambiguous, it refuses to choose and routes the decision to a human.

## Implementation status

Concord IQ is **built with Microsoft Agent Framework** as the orchestration layer
and supports **Foundry Agent Service as a first-class application runtime**. Specialist agents
coordinate through a typed casefile and call deterministic reconciliation tools.
The Agent Framework workflow runs in two modes: a **fast** mode (default, stable)
and a **strict** mode in which each specialist node executes exactly one reasoning
stage and writes its typed output into the casefile — no single call performs the
whole reasoning. Fabric IQ is the primary semantic grounding provider, with Foundry
IQ as fallback and LocalProvider for reproducible public review.

The Foundry Agent Service deployment and remote invocation are verified with
`provider_mode=replay`, `workflow_mode=strict`, a passed verifier, and all ten
specialist steps. The main backend can now route `/analyze`, `/ask`, and demo
requests to that deployment with `PROVIDER=foundry_hosted`. Guarded Foundry IQ and
Fabric IQ adapters, typed capture/replay, Fabric bootstrap helpers, optional local
narration, a deterministic verifier that blocks unsupported cases, and a per-run
agent trace are implemented. The Fabric REST and MCP surfaces are verified against
current Microsoft Learn (see [IQ integration](docs/iq-integration.md)).

The committed ReplayProvider artifact records a real Fabric IQ semantic-proof
capture over synthetic concepts. It does not claim Fabric returned the complete
scenario JSON: the Fabric ontology supplied the governed concept proof, while the
deterministic LocalProvider snapshot supplied the SQL/evidence payload.

Beyond one-off detection, Concord IQ **watches, scores, and gates**: an autonomous
portfolio scan ranks every conflict, a Concord Score grades organizational
semantic health, a natural-language chat surface grounds questions through
NL2Ontology, and a Semantic-PR approval gate merges canonical definitions only
with the configured authority owner. The reviewer workbench leads with a
deterministic meaning-fork visual: real executed counts diverge, T1.1 what-if values
move live, authority refusal leaves the fork unresolved, and an approved canonical
collapses it into one governed node.

## Why it matters

- Board meetings stall when dashboards disagree on a metric nobody has defined once.
- A naming match does not prove operational equivalence.
- A wording difference does not prove a real data conflict.
- Choosing a canonical definition is a governance decision, not a text-generation task.
- Reconciliation needs evidence: selected entities, exact SQL, impact, authority, and audit.

## What Concord IQ does

Concord IQ:

1. Resolve a business term to every registered operational definition.
2. Compare filters, time windows, grain, exclusions, source tables, and ownership.
3. Execute each definition in DuckDB and compare the resulting entity sets.
4. Reject wording-only differences when the data results are equal.
5. Quantify population and revenue impact when the results diverge.
6. Consult deterministic authority rules before proposing a canonical definition.
7. Refuse automatic reconciliation when ownership is shared, missing, or ambiguous.
8. Persist the SQL, evidence, verifier result, proposal, and audit trail.
9. Answer natural-language questions grounded in the ontology (`POST /ask`).
10. Sweep every concept and rank conflicts by business impact (`make scan`, `GET /scan`).
11. Grade organizational semantic health as a single Concord Score (`GET /score`).
12. Gate canonical definitions behind owner-only approval (`POST /proposals/{id}/approve`).
13. Promote an approved, versioned canonical meaning in Concord's registry and use it
    on the next reconciliation while preserving departmental definitions as named views.
14. Render the semantic fork as an accessible SVG driven by those same executed results,
    including exploration, refusal, equivalence, and governed convergence states.

## Beyond detection — watch, score, and gate

A conflict report gets read once. Concord IQ is built to be returned to, because
it inserts itself into a workflow teams cannot skip:

- **Ask in business terms.** `POST /ask` resolves a natural-language question
  through the ontology (NL2Ontology on Fabric IQ, deterministic locally), names
  the competing definitions, and runs the proof. Not free-text retrieval.
- **The autonomous scan.** `make scan` / `GET /scan` sweeps every governed
  concept, ranks conflicts by ARR impact, and surfaces problems nobody asked
  about — the agent that watches, not just answers.
- **The Concord Score.** `GET /score` grades organizational semantic health on a
  single 0–100 scale with a per-business-unit leaderboard.
- **Semantic pull requests.** A canonical definition is reviewed like code:
  `POST /proposals/{id}/approve|reject` merges only with the configured authority
  owner, is idempotent, promotes exactly one versioned canonical definition, and
  is written to the audit trail. A re-run uses that governed meaning; prior
  departmental variants remain named domain views. This updates Concord's own
  registry and does not claim Fabric or Foundry writeback. Ambiguous ownership is
  refused, not guessed.

All four are deterministic and evidence-backed; the LLM never decides any of them.

## The signature meaning fork

The workbench's top visual is a read-only projection of the typed casefile, not a
second reasoning engine. It labels each departmental definition with its executed
population and time window, lights the conflict edge only when SQL proves divergence,
and shows the quantified impact. Moving the deterministic what-if control updates the
same graph as an explicitly ephemeral exploration. Authorized approval collapses the
fork using the server-confirmed canonical version; the governed re-run then verifies
the canonical execution while preserving named domain views.

The SVG is keyboard-focusable, includes a visible text equivalent, and disables its
motion when the operating system requests reduced motion.

## The demo scenarios

| Business term | Seeded operational difference | Intended behavior |
| --- | --- | --- |
| Active Customer | Finance uses recent recognized revenue, Sales uses recent open/won opportunity, Customer Success uses an active contract plus qualifying usage | Detect a material three-way conflict (1,600 / 1,500 / 1,334; $33.2M ARR delta) and rank it high |
| Net Revenue | Finance and Sales wording differs while both bindings select the same seeded result | Rule it consistent by result-set equality (1,600 / 1,600) |
| Churned Customer | Finance uses contract end; Customer Success uses prolonged inactivity and grace | Detect divergence (333 / 666), then refuse because authority is shared |
| Qualified Lead | Sales counts open/won; Marketing also counts a small `nurturing` cohort | Catch the subtle 20-customer (1.3%, $2.26M) gap and quantify it |

The first three drive `make demo` and the Fabric capture set. Qualified Lead is
the "subtle catch" — it surfaces in `make scan` and the chat/`/reconcile` path
and is deliberately kept out of the capture set to keep cloud spend at six calls.
The deterministic generator creates the synthetic analytical tables and cohorts.
No real customer or tenant data is used.

## Demo in five minutes

### Prerequisites

- Docker Desktop with Docker Compose v2
- [`uv`](https://docs.astral.sh/uv/) for Python 3.12 environment management
- Node.js, pnpm, and GNU Make

### Build the local foundation

```bash
make setup
```

This installs Python dependencies, starts PostgreSQL 16, waits for readiness, and
creates the semantic registry schema.

### Regenerate synthetic analytics data

```bash
make seed
```

The command writes deterministic CSV fixtures to `data/synthetic/` and loads the
same rows into the ignored local database `data/concord_iq.duckdb`.

### Verify the reasoning core

```bash
make lint
make test
```

The suite covers seed determinism, provider and replay contracts, conflict and
equivalence verdicts, the subtle Qualified Lead catch, authority-driven refusal,
the portfolio scan and Concord Score, the owner-only approval gate, NL-query
grounding, evidence persistence, cloud budgets (including the six-call Fabric
capture), capture sanitization, context scope, the demo, and the API.

### Run all three scenarios headlessly

```bash
make demo
```

Expected verdicts:

```text
Active Customer: CONFLICT | counts=1600/1500/1334 | proposal drafted; human approval required
Net Revenue: CONSISTENT | counts=1600/1600 | decoy ruled out; no reconciliation needed
Churned Customer: CONFLICT | counts=333/666 | automatic reconciliation refused; human approval required
```

### Scan the whole semantic portfolio

```bash
make scan
```

This sweeps every concept and prints the Concord Score, the impact-ranked
conflict board (including the concepts it checked and cleared), and the per-team
semantic-health leaderboard:

```text
Concord Score: 60/100 (grade D) | 3 conflicts, 1 consistent, 1 refusal(s) across 4 concepts
  [ #1] Churned Customer   CONFLICT   ... action=refuse  authority=ambiguous
  [ #2] Active Customer    CONFLICT   ... action=propose authority=clear
  [ #3] Qualified Lead     CONFLICT   ... action=propose authority=clear
  [ ok] Net Revenue        CONSISTENT ... action=monitor authority=clear
```

### Run the reviewer workbench

```bash
make dev
```

Open `http://127.0.0.1:5173` for the UI or `http://127.0.0.1:8000/docs` for
the API. The workbench exposes provider safety, definitions, impact, the full
reasoning timeline, verifier status, governed outcome, and exact SQL evidence.

### Bootstrap Fabric and prove replay

Start with a cloud-free plan and regenerate the committed synthetic seed package:

```bash
make fabric-bootstrap-dry-run
```

After verifying current pricing, capacity, tenant permissions, and preview API
availability, copy `.env.example` to a local `.env`, authenticate with a
short-lived `FABRIC_IQ_ACCESS_TOKEN` or `az login`, and opt in:

```bash
ALLOW_CLOUD=true make fabric-bootstrap
```

The bootstrap creates or reuses the named workspace, lakehouse, and ontology
where supported, attempts the preview ontology definition import, and prints IDs
plus the ontology MCP endpoint for manual `.env` entry. It never writes `.env` or
prints the token. If preview import fails, the created resources are preserved and
the command prints a Fabric UI fallback using `fabric_seed/`.

Once the ontology is published and the MCP endpoint and fresh token are configured,
diagnose first — entity types alone carry no retrievable content, so Fabric IQ must
expose the scenario **snapshot JSON** (the bootstrap uploads
`fabric_seed/concord_iq_scenarios.json` to the lakehouse for exactly this):

```bash
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make fabric-mcp-diagnose
```

It reports one of three states — `Full snapshot JSON: FOUND`, `Semantic proof:
FOUND`, or `No useful Fabric content found` (sanitized copy in
`artifacts/replay/raw/diagnostic.json`, no tokens). Run capture once it reports
either FOUND:

```bash
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make capture
make replay-check
```

**Two honest capture modes.** Fabric IQ is used as the semantic grounding layer.
In tenants where ontology MCP returns searchable ontology concepts but not full
scenario JSON, Concord IQ records the real Fabric semantic proof (the MCP matched
`ActiveCustomer` / `NetRevenue` / `ChurnedCustomer`) and attaches the deterministic
synthetic scenario snapshot from `LocalProvider` for SQL/evidence replay — marked
transparently with `iq_proof_mode` and `snapshot_source`. Concord IQ does **not**
claim Fabric returned the full snapshot unless full-snapshot mode actually
succeeds; it claims "verified Fabric IQ semantic grounding" only after `make
capture` and `make replay-check` pass with real Fabric calls.

`make replay-check` rejects shallow connectivity captures, unverified provenance,
missing semantic evidence, missing scenarios, fake or incomplete semantic proof,
and obvious secrets before running the full demo through `ReplayProvider` with
cloud disabled. The capacity prerequisites and the F2 pause-when-idle budget
runbook (target well under EUR 100) are in
[cost controls](docs/cost-controls.md) and [IQ integration](docs/iq-integration.md).

## Architecture

The layering, from deployment down to grounding:

| Layer | Responsibility | Status |
| --- | --- | --- |
| **Foundry Agent Service** | Hosts/deploys the Agent Framework workflow | Deployment and remote replay/strict invocation verified |
| **Microsoft Agent Framework** | Orchestrates the specialist agents and workflow states (fast + strict modes) | Implemented and tested locally |
| **Concord IQ deterministic tools** | Execute SQL, evidence, authority, verifier, audit — the truth path | Implemented and tested |
| **Fabric IQ** | Primary semantic ontology grounding (ontology MCP + NL2Ontology) | Real semantic-proof capture verified; sanitized replay committed |
| **Foundry IQ** | Fallback knowledge grounding (Azure AI Search) | Adapter implemented; tenant smoke pending |
| **ReplayProvider** | Sanitized Microsoft IQ replay | Verified Fabric semantic-proof artifact committed; refuses unverified artifacts |
| **LocalProvider** | Deterministic reviewer mode over synthetic data | Implemented |

Microsoft Agent Framework owns application orchestration. Its specialist workflow
nodes pass a typed casefile and call the existing deterministic
`ReconciliationRunner` as a domain tool. The truth path remains SQL result-set
comparison plus authority-rule lookup. Optional local narration cannot alter a
conflict verdict, authority decision, or stored result.

```mermaid
flowchart TD
    UI["Chat and conflict dashboard"] --> MAF["In-process Microsoft Agent Framework workflow"]
    UI --> HOSTED["FoundryHostedProvider"]
    HOSTED --> SERVICE["Foundry Agent Service"]
    SERVICE --> MAF
    MAF --> NODES["Ten specialist workflow nodes"]
    NODES --> TOOL["reconcile_business_term tool"]
    TOOL --> ENGINE["Deterministic ReconciliationRunner"]
    ENGINE --> GROUNDING["GroundingProvider"]
    GROUNDING --> FABRIC["FabricIQProvider"]
    GROUNDING --> FOUNDRY["FoundryIQProvider fallback"]
    GROUNDING --> LOCAL["LocalProvider"]
    GROUNDING --> REPLAY["ReplayProvider"]
    LOCAL --> DUCKDB[("DuckDB synthetic analytics")]
    ENGINE --> POSTGRES[("PostgreSQL registry and evidence")]
    ENGINE --> VERIFY["Deterministic verifier"]
    VERIFY --> AUDIT["Evidence and audit trail"]
    ENGINE -. "verified facts only" .-> LLM["Disabled or Ollama narrator"]
    LLM -. "text only" .-> UI
```

![Architecture graphic placeholder](docs/assets/architecture-placeholder.svg)

### Storage split

**PostgreSQL** stores semantic and governance state:

- business units and business terms
- metric definitions and executable bindings
- ontology entities and relationships
- authority rules
- reconciliation runs and conflict findings
- evidence items, proposals, and audit events

**DuckDB** runs deterministic analytical comparisons over:

- customers
- contracts
- opportunities
- usage events
- revenue events
- churn events
- reports

## How it reasons

Microsoft Agent Framework coordinates these workflow nodes:

```text
CoordinatorAgent -> ConceptResolverAgent -> BindingInspectorAgent
-> ConflictHypothesisAgent -> DataExecutionAgent -> ImpactRankerAgent
-> AuthorityResolverAgent -> ReconciliationAgent
-> SkepticalVerifierAgent -> AuditAgent
```

The domain tool advances the existing typed reconciliation state machine:

```text
START
  -> RESOLVE_CONCEPT
  -> INSPECT_BINDINGS
  -> HYPOTHESIZE_CONFLICTS
  -> EXECUTE_DEFINITIONS
  -> RANK_IMPACT
  -> RESOLVE_AUTHORITY
  -> PROPOSE_OR_REFUSE
  -> VERIFY
  -> AUDIT
  -> COMPLETE
```

**Fast vs strict mode.** In **fast** mode (default) the coordinator invokes
`reconcile_business_term(term, period, provider)` and the framework nodes expose
the resulting trace. In **strict** mode (`CONCORD_WORKFLOW_MODE=strict`, the default
for the Foundry hosted smoke) the Agent Framework owns the progression: each
specialist node executes exactly one stage and writes its typed output into the
shared casefile — no single call performs the whole reasoning. Both modes reach
the same deterministic verdict; only the orchestration granularity differs.

**Verifier guard.** The skeptical verifier checks required evidence IDs, stored
SQL, divergent-vs-equal result sets, authority status, and proposal/refusal
validity. On failure the case is marked `blocked` or `needs_review`; a single
recovery retry is allowed for a recoverable missing-step output, and the verifier
never invents evidence to pass. Advisory language-model critique can never pass
unsupported evidence or overrule a refusal.

**Agent trace.** Every run emits a typed trace — step number, agent, input/output
summary, evidence IDs, provider mode, verifier status, and duration — persisted and
served at `GET /runs/{run_id}/agent-trace` and surfaced in the reviewer workbench,
so the multi-agent pattern is visible rather than implied.

![Reasoning timeline placeholder](docs/assets/reasoning-placeholder.svg)

## Microsoft IQ architecture

The application keeps semantic grounding and hosted runtime modes explicit:

| Provider | Role | Current status |
| --- | --- | --- |
| `LocalProvider` | Deterministic development and reviewer mode over local registry and synthetic data | Resolves concepts, returns bindings/subgraphs/rules, and executes definitions |
| `ReplayProvider` | Replays a reviewed real-IQ capture through the same typed contract | Implemented; refuses missing or unverified artifacts |
| `FabricIQProvider` | Primary cloud grounding through Fabric IQ ontology MCP + NL2Ontology | Real semantic-proof capture verified; deterministic snapshot provenance disclosed |
| `FoundryIQProvider` | Fallback cloud grounding through Azure AI Search retrieval; also contributes a live advisory governance-grounding step during authority resolution | Guarded adapter and injected-transport tests complete; advisory grounding is load-bearing while the deterministic rule still decides; tenant smoke test pending |
| `WorkIQProvider` | Work IQ grounding through Microsoft 365 Copilot Retrieval — sources the competing definitions from real M365 / Power BI artifacts | Guarded adapter and injected-transport tests complete; artifact-proof mode disclosed; tenant capture pending |
| `FoundryHostedProvider` | Calls a deployed Concord IQ Agent Framework workflow and returns its verified typed case | First-class `/analyze`, `/ask`, demo, health, and provider-status runtime |

The `nl_query` path is genuinely IQ-served: on Fabric/Foundry it calls the real
NL2Ontology/retrieve surface, while Local/Replay answer the same typed contract
deterministically. The Fabric bootstrap and adapter endpoints (create ontology,
`updateDefinition`, list items by `ItemType=Ontology`, the MCP `ontologyEndpoint`)
are confirmed against current Microsoft Learn; F2 is the minimum supported SKU.

`LocalProvider` is the reproducibility scaffold. It is not presented as Microsoft
IQ and does not satisfy the final IQ-integration goal by itself. The cloud adapters
never fall back to it silently.

The real-integration gate requires a tiny manually enabled smoke test, ignored raw
response, reviewed sanitized copy, and successful `ReplayProvider` run. See
[IQ integration](docs/iq-integration.md) and
[replay artifact policy](artifacts/replay/README.md).

## Foundry Agent Service deployment

**Foundry Agent Service is the verified cloud runtime for Concord IQ.** Microsoft
Agent Framework strict mode is the multi-agent orchestration layer. The deployed
agent runs over ReplayProvider, so invoking it does not make a Fabric call; the
separate committed replay artifact carries the verified Fabric semantic proof.
LocalProvider remains deterministic reviewer/development mode.

The deployed runtime uses **ReplayProvider**,
so the hosted agent needs **no Fabric credentials or capacity**:

```bash
make foundry-hosted-dry-run    # no cloud: checks the entrypoint + committed replay artifact, prints required env
make foundry-hosted-package    # no cloud: writes artifacts/foundry/package-report.md (what to deploy)
# after deploying, with FOUNDRY_HOSTED_ENDPOINT + FOUNDRY_ACCESS_TOKEN set:
ALLOW_CLOUD=true MAX_CLOUD_CALLS=1 make foundry-hosted-smoke   # one real call to the deployed agent
```

The hosted smoke asserts the deployed agent's response proves
**provider_mode=replay, workflow_mode=strict, term=Active Customer,
verdict=conflict, verification_status=passed, specialist_steps=10**. The
deployment runbook is in [Foundry Agent Service](docs/foundry-agent-service.md).

To route the actual backend and workbench through the hosted runtime, configure a
local, gitignored `.env`:

```text
PROVIDER=foundry_hosted
ALLOW_CLOUD=true
MAX_CLOUD_CALLS=20
FOUNDRY_HOSTED_ENDPOINT=https://<foundry-hosted-responses-endpoint>?api-version=v1
FOUNDRY_HOSTED_AGENT_ID=
FOUNDRY_ACCESS_TOKEN=<short-lived-token>
```

Then run `make dev` and open `http://127.0.0.1:5173`. The badge reads **Foundry
Agent Service / hosted runtime / Cloud enabled**, and the workbench renders the
remote typed case through the same panels used for local and replay mode.

The in-process protocol smoke (no tenant) is also available:

```bash
make foundry-agent-dry-run     # constructs the host, checks routes, no cloud, no socket
make foundry-agent-smoke       # full /responses path in process over LocalProvider (strict mode)
FOUNDRY_AGENT_PROVIDER=replay make foundry-agent-smoke   # same path over a verified replay artifact
```

It proves the chain with no tenant: **Foundry hosted entrypoint → Microsoft Agent
Framework strict workflow → Concord IQ deterministic tool → ReplayProvider /
LocalProvider → semantic reconciliation result**. Real `auto` hosting fails closed
unless cloud access, a positive budget, and a real IQ provider are explicit, and
never falls back to local silently.

## Cloud and cost safety

Cloud access starts disabled:

```text
PROVIDER=local
ALLOW_CLOUD=false
MAX_CLOUD_CALLS=0
LLM_PROVIDER=disabled
```

`FabricIQProvider`, `FoundryIQProvider`, `WorkIQProvider`, and `FoundryHostedProvider`
fail closed unless explicit cloud permission, a positive call budget, endpoint, and
authentication are configured.
Automated tests use injected transports and never call Microsoft services.

**Do not assume Foundry, Fabric, or IQ usage is free or unlimited. Verify current
Microsoft pricing, trial limits, tenant settings, and permissions before enabling
cloud mode. Keep datasets tiny, use cloud only for smoke tests, pause or delete
idle resources, and replay sanitized captured responses through ReplayProvider
for demo rehearsal.**

Raw provider responses belong in `artifacts/replay/raw/` and stay gitignored. The
reviewed, synthetic-only, secret-free capture is intentionally committed at
`artifacts/replay/sanitized/latest.json`.

A **verified Fabric IQ semantic-proof capture is committed** at
`artifacts/replay/sanitized/latest.json`. It contains no secrets (tokens, tenant
IDs, GUIDs, and emails are redacted), and it lets judges replay the verified
Fabric IQ semantic grounding **without any Fabric tenant, token, or paid
capacity**:

```bash
make replay-check
PROVIDER=replay ALLOW_CLOUD=false MAX_CLOUD_CALLS=0 make demo
```

Raw responses and diagnostics under `artifacts/replay/raw/` remain gitignored. The
complete bootstrap, capture, and replay workflow is in
[IQ integration](docs/iq-integration.md) and
[cost controls](docs/cost-controls.md).

## Reliability principles

- Fixed random seed and fixed reference date
- Synthetic data only
- Typed PostgreSQL model and provider boundaries
- Deterministic SQL as the source of truth
- Exact SQL retained as evidence
- Result-set equality for decoy rejection
- Configuration lookup for authority and refusal
- Cloud off by default
- No LLM required for core behavior
- Honest implementation-status documentation

## Optional local LLM

The core runs with `LLM_PROVIDER=disabled`. To add local proposal, verifier, and
audit explanations:

```bash
ollama pull qwen3:8b
LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3:8b make dev
```

If Ollama is unavailable, Concord IQ uses reviewed deterministic fallback text.
Narration never replaces evidence, SQL execution, verdicts, or authority rules.

## Synthetic data contract

The generator uses seed `20260606`, reference date `2026-06-01`, 2,000 customers,
stable identifiers, and deterministic cohorts, amounts, dates, regions, and
segments — enough scale for the demo numbers to read like a real board metric
while staying tiny for DuckDB and any Fabric capture. Committed CSVs make the
fixtures inspectable; the reproducible DuckDB file remains local-only.

## Project structure

```text
backend/concord/
  agents/          deterministic specialist agents
  analytics/       DuckDB execution utilities
  api/             FastAPI reconciliation and demo routes
  evals/           scenario evaluation
  llm/             disabled/local/cloud narration providers
  ms_agent/        Microsoft Agent Framework workflow and Foundry host
  orchestration/   casefile and typed state machine
  providers/       Local, Replay, Foundry IQ, Fabric IQ
  seed/            fixed-seed synthetic generator
  storage/         SQLAlchemy registry models
frontend/           React/Vite reviewer workbench
data/synthetic/    committed synthetic CSV fixtures
fabric_seed/       LocalProvider exports for tiny manual Fabric setup
tests/             deterministic acceptance tests
docs/assets/       honest graphic placeholders
docs/*.md           architecture, integration, demo, safety, submission
artifacts/replay/
  raw/             ignored captures
  sanitized/       committed reviewed replays
```

Private prompts, planning files, agent instructions, and local checkpoint memory
are excluded from version control. A clean public clone depends only on product
files.

## Hackathon alignment

**Reasoning Agents:** Microsoft Agent Framework coordinates ten typed specialist
nodes. They call the deterministic reconciliation tool for concept resolution,
binding inspection, data execution, impact ranking, authority resolution, proposal
or refusal, verification, and audit. The autonomous portfolio scan adds genuine
multi-concept reasoning beyond single-question Q&A.

**Best Use of IQ Tools:** Concord IQ spans all three Microsoft IQ layers. **Fabric
IQ** ontology + NL2Ontology is the semantic source of truth, and the `nl_query` path
is genuinely IQ-served (a real semantic-proof capture is committed). **Foundry IQ** is
the Azure AI Search knowledge layer — now *load-bearing* via a live advisory
governance-grounding step in authority resolution (the deterministic rule still
decides) — and **Work IQ** (Microsoft 365 Copilot Retrieval) sources the competing
definitions from real M365 / Power BI artifacts so a conflict comes from org content,
not a seed. The bootstrap and adapter REST/MCP
surfaces are verified against current Microsoft Learn, and Foundry Agent Service is
the deployment path. Fabric IQ is the only layer claimed verified; the Foundry IQ and
Work IQ adapters are guarded and injected-transport tested with tenant capture pending
— never overclaimed.

**Creativity and UX:** Concord IQ reasons about *meaning*, not answers — and turns
governance into a product: ask in plain English, an autonomous semantic scan, a
single Concord Score with a team leaderboard, and code-review-style approval gates.

**Reliability and safety:** The system is designed to reject false conflicts, refuse
unsupported governance choices, preserve evidence, and keep cloud access opt-in.

## Roadmap

- [x] P0: repository, storage models, deterministic seed, test, README
- [x] P1: ontology, authority rules, metric definitions, `LocalProvider`
- [x] P2: Active Customer reasoning engine and persisted evidence
- [x] P3: Net Revenue decoy, Churned Customer refusal, `make demo`
- [x] P4: demo-first React interface
- [x] P5: guarded adapters, capture/replay, and integration docs
- [x] P6: optional Ollama narration, advisory verifier critique, audit explanation
- [x] Microsoft Agent Framework orchestration and Foundry Agent Service scaffold
- [x] Fabric bootstrap dry run, synthetic seed package, and strict replay check
- [x] Enterprise-scale data and the subtle Qualified Lead conflict
- [x] Engagement layer: autonomous scan, Concord Score, Semantic-PR approval gate
- [x] Natural-language chat (`/ask`) with a genuinely IQ-served `nl_query` path
- [x] Owner-approved canonical promotion with governed re-run and preserved domain views
- [x] Accessible meaning-fork hero with live exploration, refusal, and convergence states
- [x] Fabric REST/MCP surfaces verified against Microsoft Learn; F2 budget runbook
- [ ] Real tenant capture and reviewed sanitized replay

## Limitations

- The three implemented verdicts cover fixed, reviewed synthetic scenarios rather
  than arbitrary business concepts.
- The data is synthetic and intentionally engineered for known evaluation cases.
- Behavioral equivalence is proven only over the bound data and period being tested.
- Microsoft IQ preview surfaces, pricing, permissions, and availability can change.
- The guarded adapters are not tenant-verified in this workspace.
- The Foundry Agent Service entrypoint is scaffolding and is not tenant-deployed.
- No production-readiness claim is made.

## Development approach

Concord IQ was built with modern AI-assisted tooling, with deterministic tests,
reviewable typed code, fixed-seed data, and honest status labels guarding every
change. The problem framing, architecture, and engineering decisions are the
author's.

## License

Concord IQ is licensed under the
[Apache License 2.0](LICENSE), including its explicit patent grant for
contributors and users.
