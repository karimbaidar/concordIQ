"""Typed specialist node definitions for the Agent Framework workflow."""

from collections.abc import Callable
from dataclasses import dataclass

from concord.orchestration.casefile import ReconciliationCase
from concord.orchestration.state_machine import ReconciliationState


class SpecialistNodeValidationError(RuntimeError):
    """Raised when a specialist receives an incomplete domain casefile."""


Validator = Callable[[ReconciliationCase], bool]


@dataclass(frozen=True, slots=True)
class SpecialistAgentNode:
    """Metadata and deterministic acceptance check for one workflow node."""

    name: str
    responsibility: str
    validator: Validator

    def inspect(self, case: ReconciliationCase) -> None:
        """Refuse to pass a casefile missing this specialist's required output."""
        if not self.validator(case):
            raise SpecialistNodeValidationError(
                f"{self.name} received a casefile without {self.responsibility}."
            )


SPECIALIST_AGENTS: tuple[SpecialistAgentNode, ...] = (
    SpecialistAgentNode(
        "CoordinatorAgent",
        "a typed reconciliation case and workflow plan",
        lambda case: (
            case.state
            in {
                ReconciliationState.START,
                ReconciliationState.COMPLETE,
            }
        ),
    ),
    SpecialistAgentNode(
        "ConceptResolverAgent",
        "a resolved business concept",
        lambda case: case.resolved_concept is not None,
    ),
    SpecialistAgentNode(
        "BindingInspectorAgent",
        "normalized operational bindings",
        lambda case: bool(case.binding_semantics),
    ),
    SpecialistAgentNode(
        "ConflictHypothesisAgent",
        "pairwise conflict hypotheses",
        lambda case: (
            bool(case.conflict_hypotheses)
            or (case.governed_canonical is not None and len(case.binding_semantics) == 1)
        ),
    ),
    SpecialistAgentNode(
        "DataExecutionAgent",
        "executed definition results, evidence, and deterministic hypothesis rulings",
        lambda case: (
            bool(case.execution_results)
            and bool(case.evidence)
            and (
                bool(case.conflict_hypotheses)
                or (case.governed_canonical is not None and len(case.execution_results) == 1)
            )
            and all(
                hypothesis.data_verdict in {"confirmed", "overturned"}
                and len(hypothesis.evidence_ids) == 2
                for hypothesis in case.conflict_hypotheses
            )
        ),
    ),
    SpecialistAgentNode(
        "ImpactRankerAgent",
        "a materiality assessment",
        lambda case: case.impact_assessment is not None,
    ),
    SpecialistAgentNode(
        "AuthorityResolverAgent",
        "an authority assessment",
        lambda case: case.authority_assessment is not None,
    ),
    SpecialistAgentNode(
        "ReconciliationAgent",
        "a governed proposal, refusal, or no-action decision",
        lambda case: (
            case.reconciliation_proposal is not None
            or case.refusal_reason is not None
            or case.verdict == "consistent"
        ),
    ),
    SpecialistAgentNode(
        "SkepticalVerifierAgent",
        "an explicit deterministic verifier outcome",
        lambda case: (
            case.verifier_report is not None
            and (
                case.verifier_report.passed
                or case.verification_status in {"blocked", "needs_review"}
            )
        ),
    ),
    SpecialistAgentNode(
        "AuditAgent",
        "a finalized audit timeline",
        lambda case: bool(case.audit_log),
    ),
)
