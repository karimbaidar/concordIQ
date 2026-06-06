"""Deterministic authority lookup."""

from dataclasses import dataclass

from concord.orchestration.casefile import AuthorityAssessment
from concord.providers import GroundingProvider


@dataclass(frozen=True, slots=True)
class AuthorityResolverAgent:
    """Resolve governance only from configured authority rules."""

    provider: GroundingProvider

    def run(self, concept_id: str) -> AuthorityAssessment:
        rules = tuple(self.provider.get_authority_rules(concept_id))
        canonical_rule = next(
            (rule for rule in rules if rule.semantic_dimension == "canonical-active-customer"),
            None,
        )
        if canonical_rule and canonical_rule.status == "clear" and canonical_rule.owner:
            return AuthorityAssessment(
                status="clear",
                owner=canonical_rule.owner,
                rules=rules,
                rationale=canonical_rule.rationale,
            )
        statuses = {rule.status for rule in rules}
        status = (
            "ambiguous"
            if "ambiguous" in statuses
            else "shared"
            if "shared" in statuses
            else "missing"
        )
        return AuthorityAssessment(
            status=status,
            owner=None,
            rules=rules,
            rationale="No single configured owner can approve a canonical definition.",
        )
