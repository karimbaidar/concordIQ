"""Deterministic authority lookup with an optional advisory grounding clue."""

from dataclasses import dataclass

from concord.orchestration.casefile import AuthorityAssessment
from concord.providers import AuthorityGroundingProvider, AuthorityRule, GroundingProvider


@dataclass(frozen=True, slots=True)
class AuthorityResolverAgent:
    """Resolve governance only from configured authority rules.

    The owner and status are decided strictly from the configured rules. An optional
    advisory governance clue (for example a Foundry IQ retrieval) is attached *after*
    the deterministic decision and can never change the resolved owner or status.
    """

    provider: GroundingProvider

    def run(self, concept_id: str) -> AuthorityAssessment:
        rules = tuple(self.provider.get_authority_rules(concept_id))
        assessment = self._decide(rules)
        return self._with_advisory_grounding(assessment, concept_id)

    @staticmethod
    def _decide(rules: tuple[AuthorityRule, ...]) -> AuthorityAssessment:
        canonical_rule = next(
            (rule for rule in rules if rule.semantic_dimension.startswith("canonical-")),
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

    def _with_advisory_grounding(
        self,
        assessment: AuthorityAssessment,
        concept_id: str,
    ) -> AuthorityAssessment:
        """Attach a cited governance clue without ever changing the decision."""
        if not isinstance(self.provider, AuthorityGroundingProvider):
            return assessment
        grounding = self.provider.retrieve_authority_grounding(concept_id)
        if grounding is None:
            return assessment
        grounding = grounding.model_copy(
            update={"agrees_with_rule": grounding.retrieved_owner == assessment.owner}
        )
        return assessment.model_copy(update={"advisory_grounding": grounding})
