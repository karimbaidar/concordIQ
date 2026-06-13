"""The Semantic Court: real agents argue; executed evidence rules.

The court orchestrates an adversarial, multi-role debate over a completed casefile and
records it as an auditable transcript. It is deliberately powerless over the truth path:
the verdict, authority decision, proposal, refusal, and evidence are read from the case
exactly as the deterministic engine produced them. The court explains and pressure-tests
that outcome; it can never change it. This is the safety guarantee that lets the agents
reason freely without being able to publish a fabricated result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from concord.court.roles import (
    CourtClerk,
    authority_turn,
    challengeable_bindings,
    investigator_turns,
    orchestrator_closing,
    orchestrator_opening,
    reflection_turn,
    skeptic_consensus_turn,
    skeptic_cross_examination_turns,
    steward_response_turns,
    steward_turns,
)
from concord.court.transcript import (
    DeliberationTranscript,
    DeliberationTurn,
    TranscriptMode,
    content_digest,
    now_utc,
)
from concord.llm import DisabledLLMProvider, LLMProvider
from concord.orchestration.casefile import ReconciliationCase


class CourtNotReady(ValueError):
    """Raised when a case has not completed enough stages to be deliberated."""


@dataclass(slots=True)
class SemanticCourt:
    """Run an adversarial deliberation over a completed reconciliation case."""

    llm: LLMProvider = field(default_factory=DisabledLLMProvider)

    def deliberate(self, case: ReconciliationCase) -> DeliberationTranscript:
        """Voice the debate for a completed case without altering its outcome."""
        self._require_ready(case)
        clerk = CourtClerk(self.llm)
        outcome = self._earned_outcome(case)

        turns: list[DeliberationTurn] = [orchestrator_opening(clerk, case)]
        turns.extend(steward_turns(clerk, case))
        turns.extend(investigator_turns(clerk, case))
        # The cross-examination rounds emerge from the evidence: the Skeptic challenges only
        # the stewards who claim members outside the set every definition agrees on.
        challengeable = challengeable_bindings(case) if case.verdict == "conflict" else ()
        if challengeable:
            turns.extend(skeptic_cross_examination_turns(clerk, case, challengeable))
            turns.extend(steward_response_turns(clerk, case, challengeable))
            turns.append(reflection_turn(clerk, case, len(challengeable)))
        else:
            turns.append(skeptic_consensus_turn(clerk, case))
        turns.append(authority_turn(clerk, case))
        turns.append(orchestrator_closing(clerk, case, outcome))
        frozen_turns = tuple(turns)

        concept = case.resolved_concept
        concept_id = concept.concept_id if concept else ""
        mode = (
            TranscriptMode.LIVE_CAPTURED
            if any(turn.provenance.generated for turn in frozen_turns)
            else TranscriptMode.DETERMINISTIC_FALLBACK
        )
        digest = content_digest(
            term=case.request.term,
            concept_id=concept_id,
            verdict=case.verdict,
            outcome=outcome,
            turns=frozen_turns,
        )
        return DeliberationTranscript(
            term=case.request.term,
            concept_id=concept_id,
            verdict=case.verdict,
            outcome=outcome,
            rounds=max(turn.round_no for turn in frozen_turns) + 1,
            turns=frozen_turns,
            mode=mode,
            captured_at=now_utc(),
            content_digest=digest,
        )

    @staticmethod
    def _earned_outcome(case: ReconciliationCase) -> str:
        """Read the outcome the deterministic engine already earned."""
        if case.verdict == "consistent":
            return "no_action"
        if case.reconciliation_proposal is not None:
            return "proposal"
        if case.refusal_reason:
            return "refusal"
        return "no_action"

    @staticmethod
    def _require_ready(case: ReconciliationCase) -> None:
        if not case.binding_semantics or not case.execution_results or not case.evidence:
            raise CourtNotReady("The Semantic Court needs a completed case with executed evidence.")
        if case.verdict == "incomplete":
            raise CourtNotReady("The Semantic Court cannot deliberate an incomplete verdict.")
