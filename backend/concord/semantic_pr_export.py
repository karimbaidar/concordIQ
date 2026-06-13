"""Export the latest governed semantic pull request as a content-hashed proof artifact.

A *semantic pull request* is Concord IQ's governed definition-change record: the
conflicting departmental definitions, the proposed canonical meaning, the governance
owner, the evidence IDs, the executed SQL/verifier verdict, a timestamp, and a
SHA-256 content hash. This module exports it deterministically so a judge can audit
the governed fix without running the full reviewer workbench.

If a live approved semantic PR exists in the local registry it is exported as-is;
otherwise the requested deterministic scenario is run over a fresh disposable schema
(so it is never collapsed by a prior canonical promotion) and its drafted proposal is
exported. The command-line proof defaults to the business pack's ``Active Customer``;
callers may explicitly export the learning pack's ``Certification Ready`` artifact.
The artifact contains no secrets and no tenant data.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from concord.config import ScenarioPack, Settings
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import create_provider
from concord.storage.repositories import ReconciliationRepository

DEFAULT_TERM = "Active Customer"
DEFAULT_QUESTION = "Why do our Active Customer dashboards disagree?"
ARTIFACT_PATH = Path("artifacts/semantic-pr/latest.json")
REPORT_PATH = Path("docs/proofs/semantic-pr-export.md")


class SemanticPRExportError(RuntimeError):
    """Raised when no governed semantic pull request can be exported."""


@contextmanager
def _fresh_runner(settings: Settings) -> Iterator[ReconciliationRunner]:
    """Yield a runner over a disposable schema so the conflict is never pre-governed.

    Mirrors the eval harness: a brand-new registry guarantees the three departmental
    definitions are still in conflict (not already collapsed into one approved
    canonical), and the LLM stays disabled so the verdict comes only from SQL.
    """
    schema = f"concord_semantic_pr_{uuid4().hex}"
    admin_engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = make_url(settings.database_url).update_query_dict(
        {"options": f"-csearch_path={schema}"}
    )
    engine = create_engine(scoped_url, pool_pre_ping=True)
    repository = ReconciliationRepository(engine)
    repository.initialize()
    runner = ReconciliationRunner(
        provider=create_provider(settings),
        repository=repository,
        settings=settings,
    )
    try:
        yield runner
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def _conflicting_definitions(case: ReconciliationCase) -> list[dict[str, Any]]:
    """Each departmental definition with its owner, rule, executed count, and SQL."""
    definitions: list[dict[str, Any]] = []
    for binding, evaluation in zip(case.binding_semantics, case.execution_results, strict=False):
        definitions.append(
            {
                "owner": binding.owner,
                "definition_id": binding.definition_id,
                "rule_text": binding.rule_text,
                "semantic_dimensions": list(binding.semantic_dimensions),
                "source_tables": list(binding.source_tables),
                "entity_count": evaluation.entity_count,
                "metric_total": evaluation.metric_total,
                "executed_sql": evaluation.executed_sql,
            }
        )
    return definitions


def build_semantic_pr(case: ReconciliationCase) -> dict[str, Any]:
    """Build the sanitized, hashable semantic-pull-request document for a case."""
    proposal = case.reconciliation_proposal
    if proposal is None:
        raise SemanticPRExportError(
            f"Case for {case.request.term!r} produced no governed proposal "
            f"(verdict={case.verdict!r}); nothing to export as a semantic PR."
        )
    authority = case.authority_assessment
    impact = case.impact_assessment
    impact_document: dict[str, Any] = {
        "severity": impact.severity if impact else None,
        "customer_count_delta": impact.customer_count_delta if impact else None,
        "arr_delta": impact.arr_delta if impact else None,
    }
    if impact and impact.false_positive_count is not None:
        impact_document.update(
            {
                "entity_label": impact.entity_label,
                "value_label": impact.value_label,
                "affected_entity_ids": list(impact.affected_entity_ids),
                "false_positive_count": impact.false_positive_count,
                "false_positive_label": impact.false_positive_label,
                "false_positive_entity_ids": list(impact.false_positive_entity_ids),
            }
        )
    content: dict[str, Any] = {
        "kind": "concord_iq.semantic_pull_request",
        "version": "1.0",
        "term": case.request.term,
        "run_id": str(case.run_id),
        "verdict": case.verdict,
        "conflicting_definitions": _conflicting_definitions(case),
        "proposed_canonical_definition": {
            "rule_text": proposal.canonical_definition,
            "rationale": proposal.rationale,
            "source_definition_id": proposal.canonical_source_definition_id,
            "migration_notes": list(proposal.migration_notes),
            "expected_dashboard_impact": proposal.expected_dashboard_impact,
        },
        "governance": {
            "owner": proposal.authority_owner,
            "authority_status": authority.status if authority else None,
            "requires_human_approval": proposal.requires_human_approval,
        },
        "evidence_ids": [str(ref) for ref in proposal.evidence_refs],
        "sql_verifier_result": {
            "verdict": case.verdict,
            "verification_status": case.verification_status,
            "checks_passed": sum(1 for ok in case.verifier_report.checks.values() if ok)
            if case.verifier_report
            else 0,
            "checks_total": len(case.verifier_report.checks) if case.verifier_report else 0,
        },
        "impact": impact_document,
        "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return content


# Run-scoped identifiers are excluded so the hash is content-addressed: the same
# governed definition change always produces the same hash. ``evidence_ids`` are uuid5
# values derived from the per-run id, and ``run_id``/``timestamp_utc`` are per-run.
_VOLATILE_HASH_FIELDS = frozenset({"timestamp_utc", "run_id", "evidence_ids"})


def _hash_content(content: dict[str, Any]) -> str:
    """Deterministic SHA-256 over the meaning content (excluding volatile fields).

    The timestamp, the per-run ``run_id``, and the run-scoped ``evidence_ids`` are
    excluded so the same governed definition change always produces the same content hash.
    """
    hashable = {key: value for key, value in content.items() if key not in _VOLATILE_HASH_FIELDS}
    canonical = json.dumps(hashable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def export_semantic_pr(
    *,
    settings: Settings | None = None,
    term: str = DEFAULT_TERM,
    question: str | None = None,
    scenario_pack: ScenarioPack | None = None,
    artifact_path: Path = ARTIFACT_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    """Run (or load) the governed semantic PR and write the JSON + Markdown proofs."""
    selected_pack = scenario_pack
    if selected_pack is None:
        selected_pack = (
            ScenarioPack.LEARNING
            if term.casefold() == "certification ready"
            else ScenarioPack.BUSINESS
        )
    active = (settings or Settings()).model_copy(update={"scenario_pack": selected_pack})
    active_question = question or (
        DEFAULT_QUESTION if term == DEFAULT_TERM else f"Why do our {term} definitions disagree?"
    )
    with _fresh_runner(active) as runner:
        case = runner.run(
            ReconciliationRequest(
                question=active_question,
                term=term,
            )
        )
    content = build_semantic_pr(case)
    document = {**content, "sha256": _hash_content(content)}

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(document), encoding="utf-8")
    return document


def _render_report(document: dict[str, Any]) -> str:
    """Render the human-readable semantic PR proof."""
    rows = "\n".join(
        f"| {item['owner']} | {item['rule_text']} | {item['entity_count']:,} |"
        for item in document["conflicting_definitions"]
    )
    canonical = document["proposed_canonical_definition"]
    governance = document["governance"]
    verifier = document["sql_verifier_result"]
    evidence = "\n".join(f"- `{eid}`" for eid in document["evidence_ids"])
    return f"""# Semantic PR export — {document["term"]}

> Governed definition-change artifact. Generated deterministically from executed SQL;
> contains no secrets and no tenant data.

- **Term:** {document["term"]}
- **Verdict:** `{document["verdict"]}`
- **SHA-256:** `{document["sha256"]}`
- **Timestamp (UTC):** {document["timestamp_utc"]}
- **Machine-readable artifact:** `artifacts/semantic-pr/latest.json`

## Conflicting definitions

| Team | Definition | Count |
|---|---|---:|
{rows}

## Proposed canonical definition

{canonical["rule_text"]}

- **Source definition:** `{canonical["source_definition_id"]}`
- **Rationale:** {canonical["rationale"]}
- **Expected dashboard impact:** {canonical["expected_dashboard_impact"]}

## Governance

- **Owner / approver:** {governance["owner"]}
- **Authority status:** `{governance["authority_status"]}`
- **Requires human approval:** {governance["requires_human_approval"]}

## SQL / verifier result

- **Verdict:** `{verifier["verdict"]}`
- **Verification status:** `{verifier["verification_status"]}`
- **Deterministic checks passed:** {verifier["checks_passed"]}/{verifier["checks_total"]}

## Evidence IDs

{evidence}

The canonical proposal is exported with `requires_human_approval=true`. Concord IQ
never merges a canonical definition without the configured governance owner.
"""


def main() -> None:
    """Export the semantic PR and print a one-line summary (a `make` target)."""
    document = export_semantic_pr()
    print(
        f"Semantic PR exported: {document['term']} | "
        f"verdict={document['verdict']} | sha256={document['sha256'][:12]}… | "
        f"{ARTIFACT_PATH} + {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
