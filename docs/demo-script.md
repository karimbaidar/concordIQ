# Demo script — Concord IQ

The judged artifact is the recorded video (≤5 min, your own work), never a live
tenant. Record against the local/replay stack. This file is the spine: the click
order, the screen, and the one line for each beat.

**Two honesty rules that override everything below:**
1. **No claim exceeds the build.** Only show what runs. The beat marked `PENDING`
   depends on the unbuilt T1.6 meaning-graph — do **not** record it until that lands.
   The merge-and-rerun act-loop is live in Concord's own governed registry.
2. **Never overstate the IQ layer.** Say "verified Fabric IQ semantic grounding" only
   after `make capture` + `make replay-check` pass with real Fabric calls and the badge
   reads `FabricIQProvider`. Never say Fabric returned the full snapshot unless it did.

## Before recording

```bash
make setup
make seed
make test     # 138 backend + 5 frontend green
make dev
```

Open `http://127.0.0.1:5173`. Confirm `ProviderBadge` reads `LocalProvider`, cloud
disabled, data synthetic. Keep `http://127.0.0.1:8000/docs` and a terminal for
`make scan` in a second tab for the optional closing beats.

## The spine at a glance

| # | Beat | Screen (component) | Status |
| --- | --- | --- | --- |
| 1 | The pain (board cold open) | `DashboardDisagreement` (1,600 / 1,500 / 1,334) | ✅ LIVE |
| 2 | Proven conflict + real deliberation | `DefinitionDiff`, `ReasoningTimeline` (claim→challenge→data ruling), `ImpactPanel` | ✅ LIVE (T1.2) |
| 3 | Glass-box: drag the window, watch the dollars | `DefinitionDiff` what-if slider | ✅ LIVE (T1.1) |
| 4 | It does not cry wolf (the decoy) | `DecoyRuledOut` (Net Revenue 1,600 = 1,600) | ✅ LIVE |
| 5 | It refuses rather than guess | `RefusalCard` (Churned) + `UngovernedRefusalCard` (any term) | ✅ LIVE (T1.3) |
| 6 | Governance: merge, promote, and re-run | `SemanticPullRequest` → `DashboardDisagreement` | ✅ LIVE (T1.5) |
| 7 | Score the whole org (optional) | `PortfolioBoard` / `make scan` (Concord Score 60/100) | ✅ LIVE |
| — | Cold-open hero visual | `MeaningGraph` | ⏳ `PENDING T1.6` (until then, open on beat 1) |

---

## Core spine (~3:15 — record this today)

### 1 — 0:00–0:25 · The pain (lead here, not with architecture)

Open on the workbench with the three numbers visible (`DashboardDisagreement`).

Say: *"A board decision rode on one number: Finance said 1,600 active customers.
Sales' system said 1,500. Customer Success said 1,334. Same metric, three numbers.
Nobody lied — they never agreed on what 'active' means. That gap is 266 customers and
**$33.2M** of ARR."*

> When **T1.6** lands, open on the `MeaningGraph` (one term node forking into three
> departmental nodes, lit conflict edge, $ delta) and say the same line over it.

### 2 — 0:25–1:10 · The proven conflict, and a real argument settled by data

1. `DefinitionDiff`: show the three definitions and their trailing windows
   (Finance 90 / Sales 180 / Customer Success 30 days).
2. `ReasoningTimeline`: walk one hypothesis as a **Claim → Challenge → Data ruling**
   triple — e.g. *"Confirmed: executed entity sets differ (1,600 vs 1,500)"* — with the
   **"Deterministic · LLM did not decide"** label and the exact SQL.
3. `ImpactPanel`: counts **1,600 / 1,500 / 1,334**, **$33.2M ARR delta**, ranked high.

Say: *"The agent doesn't assert the conflict — it designs the test that proves it.
A specialist claims they diverge, a skeptic demands proof, and **executed SQL** is the
referee. The model never decides the verdict; the data does."*

### 3 — 1:10–1:40 · Glass-box: edit a definition, watch the money move

1. In `DefinitionDiff`, drag the Finance time-window slider **90 → 120 days**.
2. The count re-derives live **1,600 → 1,667** (**+67 customers, +$8,567,000**); overall
   impact jumps to **333 / $41,765,000**. The **"Exploration — not governed"** chip shows.
3. Click **Reset to governed** — back to **266 / $33,198,000**.

Say: *"This is the glass box. Change one rule and the dollars re-derive instantly —
real SQL over real rows, no model in the loop. And it's clearly fenced as exploration:
nothing here touches the governed definition."*

### 4 — 1:40–2:05 · It does not cry wolf (the decoy)

1. Run **Net Revenue**. Two differently-worded definitions; executed sets are
   **equal 1,600 = 1,600** → `DecoyRuledOut`, verdict **consistent**.
2. Point to the ruling: *"Overturned: executed entity sets are equal (1,600 = 1,600)."*

Say: *"A naive tool screams CONFLICT at different wording. Concord ran both and proved
they're identical — so it earns the right to be believed when it does flag one."*

### 5 — 2:05–2:35 · It refuses rather than guess (two ways)

1. **Ambiguous authority:** open **Churned Customer** — divergent **333 / 666**, but
   ownership is shared → `RefusalCard` refuses to auto-pick a winner, routes to a human.
2. **Ungoverned term:** in the workbench search, type **"Gross Margin"** and click
   *Investigate* → `UngovernedRefusalCard`: *"Concord IQ will not guess 'Gross Margin'"*
   with the governed terms it **can** reconcile as chips.

Say: *"In a field of agents that do more autonomously, Concord is proud of what it
won't do. No owner? It refuses. No governed definition? It won't invent one. Restraint
is the feature."*

### 6 — 2:35–3:15 · Governance: the merge acts

1. Back on **Active Customer**, open `SemanticPullRequest` — the proposed canonical
   definition, evidence refs, migration checklist.
2. Show that only the **Data Governance Council** (the authority owner) can
   **Approve & merge**.
3. Point to **"Merged — canonical definition is now governed"**, Canonical v1,
   approver, timestamp, and the explicit **Concord IQ registry / no external
   writeback** label.
4. Click **Re-run with governed definition**. The conflict result becomes
   **Governed: Canonical v1** and the original Finance/Sales/Customer Success
   definitions remain visible as named domain views.

Say: *"Meaning gets a pull request. Only the owner can merge. Approval promotes one
versioned canonical definition in Concord's governed registry, records the audit event,
and the next run uses it. The old definitions remain named views — history is not
erased."*

Close: *"Enterprises built a single source of truth for **data**, but not for
**meaning**. Concord IQ proves where definitions silently disagree, settles it on data,
gates it under governance, or refuses — version control for the meaning of your metrics."*

---

## Extended beats (fold in for the ≤5:00 cut)

- **Ask in plain English (NL2Ontology).** `AskConcord`: *"Why do our active customer
  numbers disagree?"* → grounds the question in the ontology, names the competing
  definitions, runs the proof. Say: *"You ask in business terms; it resolves meaning
  against the ontology, not free-text search."*
- **The subtle catch (Qualified Lead).** Open Qualified Lead: a **20-customer / 1.3%**
  gap (Marketing counts a `nurturing` cohort Sales doesn't) — a silent **$2.26M**
  divergence, caught and quantified.
- **Score the whole org.** `PortfolioBoard` / `make scan`: **Concord Score 60/100
  (grade D)** — Churned #1, Active #2, Qualified Lead #3, Net Revenue consistent — plus
  the per-team leaderboard. Say: *"Not a one-off report — it sweeps every governed
  concept every Monday."*
- **The IQ + runtime layer.** `ProviderBadge` / `GET /providers`: Microsoft Agent
  Framework orchestrates the 10 specialist nodes; the workflow is hosted on **Foundry
  Agent Service** (`PROVIDER=foundry_hosted`); **Fabric IQ** is the semantic grounding
  layer and the committed sanitized capture replays it with no tenant. Keep the wording
  honest per rule 2.

## Beat to record only after it is built

- **Cold-open hero (`PENDING T1.6`).** Replace beat 1's static three numbers with the
  animated `MeaningGraph` fork; on the what-if (beat 3) the nodes animate; after the
  merge (beat 6) the fork collapses to a single canonical node.
