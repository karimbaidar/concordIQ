"""Phase 1 acceptance test for the subtle Qualified Lead conflict.

Marketing counts a small `nurturing` cohort that Sales does not, producing a
material-but-subtle population gap the agent must catch, quantify, and route to
a governed proposal (authority is clear, so it proposes rather than refuses).
"""

import pytest
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.orchestration.state_machine import ReconciliationState


@pytest.fixture
def qualified_lead_case(
    reconciliation_runner: ReconciliationRunner,
) -> ReconciliationCase:
    return reconciliation_runner.run(
        ReconciliationRequest(
            question="Do Sales and Marketing agree on a Qualified Lead?",
            term="Qualified Lead",
        )
    )


def test_qualified_lead_subtle_conflict(qualified_lead_case: ReconciliationCase) -> None:
    case = qualified_lead_case

    assert case.state == ReconciliationState.COMPLETE
    assert case.verdict == "conflict"
    # Sales (open/won) vs Marketing (open/won/nurturing): a small 20-customer gap.
    counts = [result.entity_count for result in case.execution_results]
    assert counts == [1500, 1520]
    assert case.impact_assessment
    assert case.impact_assessment.customer_count_delta == 20
    assert case.impact_assessment.arr_delta > 0
    assert case.verifier_report and case.verifier_report.passed is True


def test_qualified_lead_proposes_with_clear_authority(
    qualified_lead_case: ReconciliationCase,
) -> None:
    case = qualified_lead_case

    assert case.authority_assessment
    assert case.authority_assessment.status == "clear"
    assert case.authority_assessment.owner == "Revenue Operations"
    proposal = case.reconciliation_proposal
    assert proposal is not None
    assert case.refusal_reason is None
    assert proposal.requires_human_approval is True
    assert proposal.authority_owner == "Revenue Operations"
    # Conservative anchor: the narrower (Sales) definition becomes canonical.
    assert "Qualified Lead is canonically defined" in proposal.canonical_definition
    assert set(proposal.evidence_refs) == {item.evidence_id for item in case.evidence}
