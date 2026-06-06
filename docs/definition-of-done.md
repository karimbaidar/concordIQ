# Definition of done

## Deterministic MVP

- [x] Docker Compose starts PostgreSQL.
- [x] DuckDB synthetic data is fixed-seed and reproducible.
- [x] Active Customer produces a data-backed conflict.
- [x] Net Revenue is ruled equivalent by result-set equality.
- [x] Churned Customer refuses under ambiguous authority.
- [x] Exact SQL and evidence are persisted.
- [x] The skeptical verifier blocks unsupported decisions.
- [x] The headless demo prints all three verdicts.
- [x] The React workbench presents the complete casefile.

## Provider readiness

- [x] Microsoft Agent Framework is the primary API orchestration layer.
- [x] All ten specialist roles are represented as typed workflow nodes.
- [x] The existing `ReconciliationRunner` is exposed as a callable domain tool.
- [x] Foundry Agent Service deployment scaffolding fails closed by default.
- [x] Fabric IQ is preferred over the Foundry IQ fallback in automatic cloud mode.
- [x] Local, Replay, Foundry IQ, and Fabric IQ modes share one typed contract.
- [x] Cloud adapters fail closed and honor a hard request budget.
- [x] Provider readiness is visible without making cloud calls.
- [x] Replay contract matches local deterministic output in tests.
- [x] Raw capture output is gitignored.
- [x] Sanitized output requires typed validation.
- [ ] At least one real Foundry IQ or Fabric IQ run is captured.
- [ ] The reviewed sanitized capture is committed and shown in the README/demo.

## Public repository

- [x] Product source, tests, synthetic data, and product docs are public.
- [x] Planning prompts and local checkpoint memory are ignored.
- [x] No secrets, tenant identifiers, or confidential data are committed.
- [x] Cloud and cost limitations are documented.
- [x] Architecture documentation includes Mermaid diagrams.
- [ ] A public license is selected.

## Optional narration

- [x] `DisabledLLMProvider` is the default and makes no network request.
- [x] `OllamaLLMProvider` uses the local structured chat API.
- [x] Decision, verifier, and audit narration carries explicit provenance.
- [x] Ollama failure falls back without breaking reconciliation.
- [x] Tests prove generated text cannot override evidence or deterministic decisions.

## Release gate

P5 is not fully complete until the two unchecked real-capture items are satisfied.
Passing mocked adapter tests proves contract behavior and cloud guards; it does
not prove tenant configuration or a successful Microsoft IQ call.
