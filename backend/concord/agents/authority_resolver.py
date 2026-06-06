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
        clear_owners = {rule.owner for rule in rules if rule.status == "clear" and rule.owner}
        if rules and all(rule.status == "clear" for rule in rules) and len(clear_owners) == 1:
            owner = clear_owners.pop()
            return AuthorityAssessment(
                status="clear",
                owner=owner,
                rules=rules,
                rationale=f"{owner} is the configured authority for this concept.",
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
