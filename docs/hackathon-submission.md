# Hackathon submission draft

## Project

**Concord IQ — the semantic reconciliation agent for enterprise meaning**

Concord IQ detects when business teams use the same term with different
operational meanings. It compares executable definitions, tests them against
synthetic data, ranks business impact, consults authority rules, and proposes or
refuses a governed semantic reconciliation.

## Track alignment

### Reasoning Agents

The agent uses a typed state machine and specialist roles for concept resolution,
binding inspection, conflict hypothesis, data execution, impact ranking,
authority resolution, reconciliation, skeptical verification, and audit.

### Best Use of IQ Tools

The architecture includes guarded adapters for:

- Azure AI Search knowledge bases used by Foundry IQ
- Fabric IQ ontology MCP

`ReplayProvider` is designed to preserve a reviewed real-IQ response for
zero-spend rehearsal. `LocalProvider` is clearly labeled deterministic reviewer
mode and is not represented as Microsoft IQ.

## Demonstrated behavior

- **Active Customer:** detects a material 96/90/80 conflict and drafts a proposal.
- **Net Revenue:** rejects a wording-only decoy with equal 96/96 results.
- **Churned Customer:** detects a 20/40 conflict and refuses because authority is
  shared or ambiguous.
- Every completed case retains executed SQL, evidence, verifier checks, and audit.
- Cloud calls are impossible under default configuration.

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

The adapter code and contract tests are complete, but the development workspace
did not have a Microsoft tenant or IQ resource available for the required real
smoke capture. No real-integration claim should be made until a sanitized capture
is committed and demonstrated through `ReplayProvider`.

## Future work

- complete the real IQ smoke capture
- add broader ontology and definition authoring
- support arbitrary evaluation periods in replay packages
- add optional local narration over verified evidence
- add authenticated multi-user governance workflows
