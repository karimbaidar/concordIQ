# Five-minute demo script

The judged artifact is the recorded video, never a live tenant. Record against
the local/replay stack. This script is the click order and the line for each beat.

## Before recording

```bash
make setup
make seed
make test     # 65 backend + 2 frontend green
make dev
```

Open `http://127.0.0.1:5173`. Confirm the `ProviderBadge` reads `LocalProvider`,
cloud disabled, data synthetic. Keep `make scan` and `http://127.0.0.1:8000/docs`
in a second terminal/tab for the closing beats.

If a sanitized Fabric capture is committed, also run `make replay-check` and have
`PROVIDER=replay make dev` ready so the badge can read `FabricIQProvider`.

## 0:00–0:30 — The pain

Say: *"Before a board meeting, three dashboards disagree on Active Enterprise
Customers: Finance 1,600, Sales 1,500, Customer Success 1,334. Same metric, three
numbers. The data is fine — the **definitions** disagree, and nobody reconciled
them."*

Show the `DashboardDisagreement` hook with the three numbers.

## 0:30–1:10 — Ask in plain English (NL2Ontology)

1. In the **Ask Concord IQ** box, type *"Why do our active customer numbers
   disagree?"* (or click the suggestion chip).
2. Concord IQ grounds the question in the ontology, names the three competing
   definitions, then runs the full reconciliation and drops you into the workbench.

Say: *"You ask in business terms. It resolves the meaning against the ontology —
not free-text search — then proves the answer on data."*

## 1:10–2:20 — The proven conflict

1. Show the three definitions and their 30 / 90 / 180-day windows in the
   `DefinitionDiff`.
2. Point to executed counts **1,600 / 1,500 / 1,334** and the **$33.2M ARR delta**
   in the `ImpactPanel` (ranked high).
3. Walk the ten-state `ReasoningTimeline` and the green skeptical-verifier badge.
4. Expand one evidence item to show the exact SQL.

Say: *"The conflict is decided by executing both definitions and comparing the
result sets — behaviour on data, not wording. Every claim has stored SQL."*

## 2:20–2:55 — It does not cry wolf (the decoy)

1. Return home; ask *"Are our net revenue definitions equivalent?"*
2. Show the two differently-worded definitions and the **equal 1,600 / 1,600**
   result sets and equal totals → **consistent, no action**.

Say: *"A naive tool screams CONFLICT on different wording. Concord runs both and
proves they are identical. It earns the right to be believed when it does flag
one."*

## 2:55–3:30 — The subtle catch (Qualified Lead)

1. From the autonomous board (or ask *"Do Sales and Marketing agree on a qualified
   lead?"*), open **Qualified Lead**.
2. Show the small **20-customer / 1.3%** gap: Marketing counts a `nurturing`
   cohort that Sales does not — a silent **$2.26M** divergence — caught and
   quantified, and (authority is clear) drafted as a proposal.

Say: *"It does not only catch the obvious three-way splits. It catches the silent
one-status-value gaps too, and tells you exactly what they cost."*

## 3:30–4:00 — Governance: refuse, then gate

1. Open **Churned Customer**: divergent **333 / 666** populations, but authority
   is shared/ambiguous → the `RefusalCard` refuses to auto-pick a winner.
2. Back on a clear-authority case (Active Customer), open the
   `SemanticPullRequest`: only the **authority owner** can **Approve & merge**;
   the decision is recorded in the audit trail.

Say: *"Definitions get reviewed like code. The agent refuses when no one owns the
call, and gates the merge to the owner when someone does."*

## 4:00–4:35 — Watch and score the whole org

1. Run `make scan` in the terminal (or show the `PortfolioBoard`):
   **Concord Score 60/100 (grade D)** — Churned #1, Active #2, Qualified Lead #3,
   Net Revenue consistent — plus the per-team leaderboard.

Say: *"This isn't a one-off report. It sweeps every governed concept, scores your
semantic health, and ranks who has the most unreconciled meaning. That's the
thing people open every Monday."*

## 4:35–5:00 — The IQ layer and the close

Point to the `ProviderBadge` / `GET /providers`:

- Microsoft Agent Framework orchestrates the specialist workflow.
- **Fabric IQ** ontology + NL2Ontology is the semantic source of truth; the
  `nl_query` path is genuinely IQ-served. REST/MCP surfaces are verified against
  current Microsoft Learn (see `docs/iq-integration.md`).
- Foundry IQ is the fallback; Local is reproducibility mode; Replay shows a
  sanitized real-IQ capture; cloud is off until an operator opts in with a budget.

Only claim a real IQ smoke test if the sanitized artifact is committed and the
badge reads `FabricIQProvider`.

Close: *"Concord IQ finds where your enterprise's definitions silently disagree —
proves it on data, scores it, and either reconciles it under governance or refuses.
It's a single source of truth for **meaning**."*
