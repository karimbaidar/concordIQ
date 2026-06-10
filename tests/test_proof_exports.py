"""Tests for the judge-proof, semantic PR export, and Work IQ proof runners.

These cover the deterministic, cloud-free logic: semantic PR building/hashing over a
real conflict case, Work IQ status parsing, and judge-proof report rendering and
sanitization. No test makes a cloud call.
"""

import json
from pathlib import Path

import pytest
from concord.config import Settings
from concord.judge_proof import JudgeProof, StepResult, _summary
from concord.orchestration.runner import ReconciliationRunner
from concord.semantic_pr_export import (
    SemanticPRExportError,
    build_semantic_pr,
    export_semantic_pr,
)
from concord.work_iq_proof import (
    _is_license_error,
    _retrieval_hit_count,
    run_work_iq_proof,
)


def _no_cloud_settings() -> Settings:
    return Settings(_env_file=None, allow_cloud=False, max_cloud_calls=0)


# --- semantic PR export ---------------------------------------------------


def test_semantic_pr_export_writes_signed_artifact(
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "semantic-pr.json"
    report = tmp_path / "semantic-pr.md"
    document = export_semantic_pr(
        settings=reconciliation_runner.settings,
        artifact_path=artifact,
        report_path=report,
    )

    assert document["term"] == "Active Customer"
    assert document["verdict"] == "conflict"
    assert len(document["conflicting_definitions"]) == 3
    owners = {item["owner"] for item in document["conflicting_definitions"]}
    assert owners == {"Finance", "Sales", "Customer Success"}
    assert document["governance"]["requires_human_approval"] is True
    assert len(document["sha256"]) == 64
    assert document["evidence_ids"]

    written = json.loads(artifact.read_text(encoding="utf-8"))
    assert written["sha256"] == document["sha256"]
    assert "Active Customer" in report.read_text(encoding="utf-8")


def test_semantic_pr_hash_is_stable_across_runs(
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
    tmp_path: Path,
) -> None:
    settings = reconciliation_runner.settings
    first = export_semantic_pr(
        settings=settings,
        artifact_path=tmp_path / "a.json",
        report_path=tmp_path / "a.md",
    )
    second = export_semantic_pr(
        settings=settings,
        artifact_path=tmp_path / "b.json",
        report_path=tmp_path / "b.md",
    )
    # The content hash excludes the volatile timestamp, so it is reproducible.
    assert first["sha256"] == second["sha256"]


def test_build_semantic_pr_requires_a_proposal(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest

    case = ReconciliationCase(request=ReconciliationRequest(question="?", term="Active Customer"))
    with pytest.raises(SemanticPRExportError):
        build_semantic_pr(case)


# --- Work IQ proof --------------------------------------------------------


def test_is_license_error_matches_graph_message() -> None:
    assert _is_license_error("Authorization Failed - User does not have valid license")
    assert not _is_license_error("403 Forbidden: insufficient privileges")


def test_retrieval_hit_count_counts_hits() -> None:
    assert _retrieval_hit_count({"retrievalHits": [{"webUrl": "a"}, {"webUrl": "b"}]}) == 2
    assert _retrieval_hit_count({"retrievalHits": []}) == 0
    assert _retrieval_hit_count({"error": "nope"}) == 0


def test_work_iq_proof_skips_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Redirect the committed-doc and status sinks so the test never touches the repo.
    monkeypatch.setattr("concord.work_iq_proof.STATUS_PATH", tmp_path / "status.json")
    monkeypatch.setattr("concord.work_iq_proof.LICENSE_GATE_PATH", tmp_path / "gate.md")
    document = run_work_iq_proof(_no_cloud_settings())
    assert document["status"] == "skipped"
    assert document["mode"] == "optional_m365_artifact_grounding"
    assert (tmp_path / "gate.md").exists()


# --- judge proof ----------------------------------------------------------


def _proof_with_local(*statuses: tuple[str, str]) -> JudgeProof:
    proof = JudgeProof(settings=_no_cloud_settings())
    proof.steps = [
        StepResult(key=key, label=key, status=status, mandatory=True) for key, status in statuses
    ]
    proof.foundry = {"status": "skipped", "mode": "hosted_runtime"}
    proof.fabric = {"status": "passed", "mode": "sanitized_replay", "live": "skipped"}
    proof.work_iq = {"status": "license_gated", "mode": "optional_m365_artifact_grounding"}
    return proof


def test_judge_proof_mandatory_gate() -> None:
    passing = _proof_with_local(("tests", "passed"), ("eval", "passed"))
    assert passing.mandatory_passed is True
    failing = _proof_with_local(("tests", "passed"), ("eval", "failed"))
    assert failing.mandatory_passed is False


def test_judge_proof_json_shape() -> None:
    proof = _proof_with_local(("tests", "passed"))
    document = proof.to_json("abc123", "2026-06-10T00:00:00Z")
    assert document["commit"] == "abc123"
    assert document["fabric_iq"]["mode"] == "sanitized_replay"
    assert document["work_iq"]["status"] == "license_gated"
    assert document["foundry_agent_service"]["status"] == "skipped"


def test_judge_proof_report_has_no_secret_shaped_text() -> None:
    proof = _proof_with_local(("tests", "passed"))
    markdown = proof._render_markdown("abc123", "2026-06-10T00:00:00Z")
    lowered = markdown.lower()
    assert "bearer " not in lowered
    assert "authorization:" not in lowered
    assert "license-gated" in lowered


def test_judge_proof_summary_renders_statuses() -> None:
    proof = _proof_with_local(("tests", "passed"))
    summary = _summary(proof.to_json("abc123", "2026-06-10T00:00:00Z"))
    assert "Concord IQ judge proof" in summary
    assert "Work IQ:" in summary
    assert "LICENSE-GATED" in summary
