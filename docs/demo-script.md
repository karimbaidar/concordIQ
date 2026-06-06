# Five-minute demo script

## Before the demo

```bash
make setup
make seed
make test
make dev
```

Open `http://127.0.0.1:5173`. Confirm the provider badge says
`LocalProvider`, cloud is disabled, and data is synthetic.

## 0:00–0:35 — The problem

Say: “Enterprises created a single source of truth for data, but not for
meaning. Concord IQ finds when teams share a term but not an operational
definition.”

Point to the three terms in the scenario selector.
If Ollama is enabled, point out its model name in the runtime badge. Otherwise,
explain that deterministic narration fallback is active.

## 0:35–2:10 — Active Customer

1. Select **Active Customer** and run reconciliation.
2. Show the three definitions and 30/90/180-day differences.
3. Point out the executed counts: 96, 90, and 80.
4. Show high impact and the affected reports.
5. Walk through the ten-state reasoning timeline and verifier pass.
6. Open the draft semantic pull request and emphasize human approval.
7. Expand one evidence item to show exact SQL.
8. Show the evidence narration panel and its provenance label.

Judge takeaway: the conflict is proven by data, not guessed from wording.

## 2:10–3:05 — Net Revenue decoy

1. Select **Net Revenue** and run reconciliation.
2. Show that the wording differs.
3. Show equal 96/96 entity sets and equal totals.

Judge takeaway: Concord IQ can rule out a false conflict.

## 3:05–4:00 — Churned Customer refusal

1. Select **Churned Customer** and run reconciliation.
2. Show divergent 20/40 populations.
3. Show shared or ambiguous authority.
4. Show the refusal card and required human approval.

Judge takeaway: the agent does not invent governance authority.

## 4:00–4:35 — IQ architecture

Open `GET /providers` in the API docs. Explain:

- Local is reproducibility mode.
- Replay is for a sanitized real-IQ capture.
- Foundry uses Azure AI Search knowledge-base retrieval.
- Fabric uses the ontology MCP endpoint.
- Cloud remains off until an operator explicitly enables a budget.

Do not claim a real IQ smoke test until the sanitized artifact is present.

## 4:35–5:00 — Close

Say: “Concord IQ detects semantic drift, tests it against data, ranks its
business impact, and either proposes a governed reconciliation or refuses.”

End on the evidence and verifier panels.
