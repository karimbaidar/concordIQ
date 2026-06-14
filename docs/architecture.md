# Concord IQ architecture

Concord IQ is a learning and certification governance system built around one
rule: agents may investigate and explain, but deterministic evidence owns the
verdict. The primary demonstration reconciles three operational definitions of
**Certification Ready** over a fixed, synthetic 120-learner workbench case.

Microsoft Fabric IQ grounds the business concept and its relationships. Microsoft
Agent Framework coordinates two distinct reasoning workflows. Exact SQL, entity-set
comparison, configured authority, skeptical verification, and human approval remain
outside model control.

## Learning system view

```mermaid
flowchart LR
    subgraph SOURCES["Enterprise learning meaning sources"]
        HR["HR<br/>80 claimed ready"]
        LD["Learning and Development<br/>56 selected"]
        MGR["Managers<br/>56 selected<br/>different learner IDs"]
    end

    FABRIC["Microsoft Fabric IQ<br/>Ontology and semantic concept grounding<br/><b>Grounds meaning; does not decide the verdict</b>"]

    subgraph ENGINE["Concord IQ deterministic evidence engine"]
        BIND["Trusted definition bindings"]
        SNAP["Fixed 120-learner synthetic snapshot"]
        SQL["Exact SQL execution"]
        SETS["Entity-set comparison<br/>Equal counts do not imply equal populations"]
        EVID["Evidence records<br/>80 / 56 / 56<br/>24 false-ready<br/>$10,800 synthetic voucher risk"]
        BIND --> SQL
        SNAP --> SQL
        SQL --> SETS --> EVID
    end

    subgraph PHASE1["Phase 1: Analyze Disagreement"]
        AF1["Microsoft Agent Framework<br/>10-stage reconciliation"]
        VERIFY["Skeptical verifier<br/>Deterministic blocking checks"]
        AF1 --> VERIFY
    end

    HOST["Microsoft Foundry Agent Service<br/>Hosts Phase 1 over verified replay"]
    CASE["Frozen verifier-approved case<br/>Verdict, populations, evidence IDs,<br/>SQL citations, impact, authority, proposal"]

    subgraph PHASE2["Phase 2: Convene the Semantic Court"]
        AF2["Separate Microsoft Agent Framework graph"]
        COURT["Stewards, investigator, skeptic,<br/>reflection, authority, Court audit"]
        AF2 --> COURT
    end

    OWNER["Learning Governance Council<br/>Human owner approval"]
    PR["Semantic PR"]
    CANON["Canonical Definition v1<br/>Concord IQ registry only"]
    RERUN["Governed local rerun"]

    HR --> FABRIC
    LD --> FABRIC
    MGR --> FABRIC
    FABRIC --> ENGINE
    ENGINE --> PHASE1
    HOST -. "deployed strict workflow" .-> AF1
    VERIFY --> CASE
    CASE --> PHASE2
    COURT --> OWNER
    OWNER --> PR --> CANON --> RERUN

    SCALE["Separate Fabric-bound scale artifact<br/>10,000 synthetic learners<br/>522 canonical-ready<br/>4,334 false-ready records<br/><b>Not the 120-learner workbench execution</b>"]
    SCALE -. "separate proof surface" .-> PHASE1
```

The `$10,800` value belongs only to the 24-learner difference in the 120-learner
workbench case. It is not derived from, or combined with, the separate 10,000-row
Fabric scale artifact.

## Exact case lifecycle

```mermaid
sequenceDiagram
    autonumber

    actor Reviewer
    participant UI as React Workbench
    participant API as FastAPI
    participant IQ as Fabric IQ / Replay / Local
    participant WF1 as Phase 1 Agent Framework
    participant SQL as DuckDB Evidence Engine
    participant DB as PostgreSQL and Case Cache
    participant WF2 as Semantic Court Agent Framework
    actor Owner as Learning Governance Council

    Reviewer->>UI: Analyze Certification Ready
    UI->>API: POST /analyze
    API->>IQ: Resolve concept and competing bindings
    IQ-->>API: HR, L&D, and Managers definitions with provenance
    API->>WF1: Start typed 10-stage casefile
    WF1->>SQL: Execute trusted bindings
    SQL-->>WF1: Entity IDs, counts, exact SQL, evidence IDs
    WF1->>WF1: Rank impact, resolve authority, verify, audit
    WF1->>DB: Persist and cache verifier-approved case by run_id
    DB-->>API: Frozen case: 80 / 56 / 56, conflict, 24, $10,800
    API-->>UI: Evidence workflow complete

    Reviewer->>UI: Convene the Semantic Court
    UI->>API: POST /runs/{run_id}/court
    API->>DB: Load the exact frozen case
    DB-->>API: Verifier-approved casefile
    API->>WF2: Deliberate over frozen evidence
    Note over WF2,SQL: No SQL rerun and no second reconciliation
    WF2->>WF2: Evidence-selected branches and optional one-time replan
    WF2->>WF2: Audit verdict, outcome, authority, and exact citations
    WF2-->>API: Grouped, digest-sealed Court transcript
    API-->>UI: No new verdict and no duplicate proposal

    Owner->>API: Approve Semantic PR
    API->>DB: Promote one versioned canonical definition
    DB-->>UI: Canonical Definition v1
    Reviewer->>API: POST /runs/{run_id}/governed-rerun
    API->>SQL: Execute through local deterministic registry
    SQL-->>UI: Governed result with domain views preserved
```

Completed verifier-approved cases are held in a bounded runtime cache keyed by
`run_id`. An unknown or expired run returns a friendly `404`; an incomplete or
unverified case returns `409`. A verified Foundry-hosted case is imported
idempotently into the local Concord IQ registry so the configured owner can approve
it. The governed rerun is deliberately local and performs no Fabric or Foundry
writeback.

## Phase 1: evidence workflow

The first Microsoft Agent Framework graph produces the governed case:

```mermaid
flowchart LR
    C["1. CoordinatorAgent"] --> R["2. ConceptResolverAgent"]
    R --> B["3. BindingInspectorAgent"]
    B --> H["4. ConflictHypothesisAgent"]
    H --> D["5. DataExecutionAgent"]
    D --> I["6. ImpactRankerAgent"]
    I --> A["7. AuthorityResolverAgent"]
    A --> P["8. ReconciliationAgent"]
    P --> V["9. SkepticalVerifierAgent"]
    V --> U["10. AuditAgent"]

    D -. "exact SQL and entity sets" .-> E[("Deterministic evidence")]
    E -. "blocks unsupported output" .-> V
```

The conflict hypothesis stage records a claim, a skeptical challenge, and the
eventual data ruling. SQL result-set equality settles the ruling. The verifier
checks evidence completeness, result-set behavior, authority consistency, proposal
validity, and impact derivation before the case can be shown as complete.

Foundry Agent Service hosts this ten-stage strict workflow over the verified
Certification Ready replay. It does not host the second Court graph.

## Phase 2: Semantic Court

The Court is a separate Agent Framework graph over the frozen case:

```mermaid
flowchart TD
    C["CourtCoordinatorAgent"] --> S["StewardPanelAgent"]
    S --> P["InvestigatorPlanAgent"]
    P --> E["EvidenceReviewAgent"]
    E --> Q{"Unresolved comparison?<br/>Including equal counts with unequal IDs"}
    Q -- "yes, once at most" --> RP["InvestigatorReplanAgent"]
    RP --> B{"Frozen verdict"}
    Q -- "no" --> B
    B -- "conflict" --> SK["SkepticAgent"]
    SK --> SR["StewardResponseAgent"]
    SR --> RF["ReflectionAgent"]
    B -- "consistent" --> SC["SkepticConsensusAgent"]
    RF --> A["AuthorityAgent"]
    SC --> A
    A --> CA["CourtAuditAgent"]
    CA --> T["Digest-sealed transcript"]

    FROZEN[("Frozen verifier-approved case")] --> C
    FROZEN -. "verdict, evidence, authority,<br/>and proposal cannot change" .-> CA
```

For the Certification Ready conflict:

- HR narrows its enterprise claim after the 24-person false-ready finding.
- Managers reframe their result as an operational domain view.
- Learning and Development defends the proposed canonical candidate but defers
  publication to the Learning Governance Council.
- Ambiguous authority produces no winner; the authority agent preserves the
  engine's refusal.

`CourtAuditAgent` recomputes a digest over engine-owned facts and proves that the
Court outcome, verdict, authority, proposal state, and exact evidence citations
still match the original case. Model narration is optional. Deterministic fallback
narration traverses the same Agent Framework graph.

## Provider and provenance model

| Reviewer label | Meaning |
| --- | --- |
| Fabric IQ Live | Fabric ontology match with deterministic local snapshot execution |
| Fabric Replay | Sanitized, verified Fabric capture replay with no cloud call |
| Foundry Agent Service Live | Hosted Phase 1 Agent Framework workflow over verified replay |
| Local | Fully local grounding and deterministic execution |

`FabricIQProvider`, `ReplayProvider`, and `LocalProvider` implement the same typed
grounding contract. Fabric IQ supplies semantic grounding; the displayed learner
populations are computed by Concord IQ's deterministic evidence path. Foundry IQ
authority grounding is advisory only and cannot replace the configured authority
rule. Work IQ is implemented behind a fail-closed adapter but remains license-gated
and is not claimed as a completed live retrieval.

Optional model narration receives verified facts only. Its result type contains
text and provenance, not verdicts, authority choices, evidence sets, impact values,
or approval decisions.

## Trust and storage boundaries

- **DuckDB** holds fixed-seed synthetic learning data and executes trusted SQL.
- **PostgreSQL** stores cases, exact evidence, proposals, canonical versions, agent
  traces, and audit events.
- **RuntimeManager** caches a bounded set of completed cases for exact-run Court
  deliberation.
- **The Concord IQ registry** is the only system changed by approval.
- **Fabric IQ and Foundry Agent Service** receive no automatic writeback.
- **Cloud is off by default** and every cloud adapter requires explicit permission,
  authentication, an endpoint, and a positive call budget.

See [IQ integration](iq-integration.md), [Foundry Agent Service](foundry-agent-service.md),
[cloud runtime](cloud-runtime.md), and [threat model](threat-model.md).
