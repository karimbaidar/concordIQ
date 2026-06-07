# Hackathon submission draft

## Project

**Concord IQ — the semantic reconciliation agent for enterprise meaning**

Concord IQ detects when business teams use the same term with different
operational meanings. It compares executable definitions, tests them against
synthetic data, ranks business impact, consults authority rules, and proposes or
refuses a governed semantic reconciliation. It then goes further than a one-off
report: it **watches** (an autonomous portfolio scan), **scores** (a single
Concord Score with a per-team leaderboard), **answers** in business terms (an
NL2Ontology-grounded chat), and **gates** canonical definitions behind
code-review-style, owner-only approval.

## Track alignment

### Reasoning Agents

Microsoft Agent Framework coordinates ten typed specialist workflow nodes for
concept resolution, binding inspection, conflict hypothesis, data execution,
impact ranking, authority resolution, reconciliation, skeptical verification,
and audit. The existing deterministic runner is exposed as their domain tool.

### Best Use of IQ Tools

The architecture uses:

- Fabric IQ ontology MCP + NL2Ontology as the primary semantic grounding provider.
  The `nl_query` / `POST /ask` path is genuinely IQ-served: on Fabric/Foundry it
  calls the real NL2Ontology/retrieve surface.
- Foundry IQ knowledge-base retrieval as the fallback IQ provider.
- Foundry Agent Service as the deployment path.

The bootstrap and adapter REST/MCP surfaces (create ontology, `updateDefinition`,
list items by `ItemType=Ontology`, the MCP `ontologyEndpoint`) are verified
against current Microsoft Learn, and F2 is confirmed as the minimum supported SKU.
`ReplayProvider` is designed to preserve a reviewed real-IQ response for
zero-spend rehearsal. `LocalProvider` is clearly labeled deterministic reviewer
mode and is not represented as Microsoft IQ.

### Creativity, originality, and UX

Few entries make semantic *meaning itself* the object of reasoning. Concord IQ
also turns governance into a product people return to: ask in plain English, an
autonomous semantic scan that finds problems nobody asked about, a single Concord
Score with a team leaderboard, and approval gates that merge meaning like code.

## Demonstrated behavior

- **Active Customer:** detects a material 1,600 / 1,500 / 1,334 conflict ($33.2M
  ARR delta) and drafts a proposal.
- **Net Revenue:** rejects a wording-only decoy with equal 1,600 / 1,600 results.
- **Churned Customer:** detects a 333 / 666 conflict and refuses because authority
  is shared or ambiguous.
- **Qualified Lead:** catches a subtle 20-customer (1.3%, $2.26M) gap from one
  status value and quantifies it.
- **Autonomous scan + Concord Score:** sweeps all concepts to a 60/100 (grade D)
  health score with an impact-ranked board and per-team leaderboard.
- **NL chat:** `POST /ask` grounds a business question through NL2Ontology, then
  reconciles it on data.
- **Approval gate:** `POST /proposals/{id}/approve|reject` merges canonical
  definitions only with the configured authority owner, recorded in the audit log.
- Every completed case retains executed SQL, evidence, verifier checks, and audit.
- Cloud calls are impossible under default configuration.
- The HTTP API executes through the Microsoft Agent Framework workflow.

## Reliability

- fixed-seed synthetic data
- typed provider and casefile contracts
- deterministic SQL result-set comparison
- deterministic authority and refusal rules
- no LLM required for core behavior
- hard cloud request budget
- raw capture isolation and sanitized replay validation
- optional local Ollama narration with a text-only output contract
- deterministic fallback when Ollama is unavailable or returns invalid output

## Current limitation

The adapter code and contract tests are complete, and the Fabric REST/MCP surfaces
are verified against current Microsoft Learn — but the development workspace had no
Microsoft tenant or IQ resource available for the required real smoke capture. No
real-integration claim should be made until a sanitized capture is committed and
demonstrated through `ReplayProvider`. The Foundry Agent Service entrypoint is
scaffolding and has not been tenant-deployed.

## Future work

- complete the real IQ smoke capture
- add broader ontology and definition authoring
- support arbitrary evaluation periods in replay packages
- add optional local narration over verified evidence
- add authenticated multi-user governance workflows
