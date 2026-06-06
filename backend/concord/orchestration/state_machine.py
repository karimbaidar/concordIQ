"""Explicit state transitions for the reconciliation reasoning graph."""

from enum import StrEnum


class InvalidStateTransition(RuntimeError):
    """Raised when orchestration tries to skip or reorder a reasoning state."""


class ReconciliationState(StrEnum):
    START = "START"
    RESOLVE_CONCEPT = "RESOLVE_CONCEPT"
    INSPECT_BINDINGS = "INSPECT_BINDINGS"
    HYPOTHESIZE_CONFLICTS = "HYPOTHESIZE_CONFLICTS"
    EXECUTE_DEFINITIONS = "EXECUTE_DEFINITIONS"
    RANK_IMPACT = "RANK_IMPACT"
    RESOLVE_AUTHORITY = "RESOLVE_AUTHORITY"
    PROPOSE_OR_REFUSE = "PROPOSE_OR_REFUSE"
    VERIFY = "VERIFY"
    AUDIT = "AUDIT"
    COMPLETE = "COMPLETE"


STATE_SEQUENCE = tuple(ReconciliationState)
NEXT_STATE = dict(zip(STATE_SEQUENCE, STATE_SEQUENCE[1:], strict=False))


def require_transition(
    current: ReconciliationState,
    requested: ReconciliationState,
) -> None:
    """Enforce the P2 DAG's single deterministic happy path."""
    expected = NEXT_STATE.get(current)
    if requested != expected:
        raise InvalidStateTransition(
            f"Invalid transition {current.value} -> {requested.value}; "
            f"expected {expected.value if expected else 'no further state'}."
        )
