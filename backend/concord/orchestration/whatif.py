"""Ephemeral deterministic re-derivation for one copied local binding."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from concord.providers import DefinitionBinding, EvaluationPeriod, LocalProvider

EXPLORATION_NOTE = "Exploration only — not governed, not persisted, no proposal, no audit."


class WhatIfOverrides(BaseModel):
    """The deliberately small override whitelist."""

    model_config = ConfigDict(extra="forbid")

    time_window_days: int = Field(ge=30, le=180)


class WhatIfRequest(BaseModel):
    """One local, read-only definition experiment."""

    term: str
    binding_id: str
    overrides: WhatIfOverrides


class WhatIfMetric(BaseModel):
    """One deterministic population and metric total."""

    entity_count: int
    metric_value: float


class WhatIfDelta(BaseModel):
    """Signed change from the governed binding to the copied binding."""

    entity_count: int
    metric_value: float


class WhatIfResult(BaseModel):
    """Non-persisted proof returned to the glass-box workbench."""

    term: str
    binding_id: str
    overrides: WhatIfOverrides
    baseline: WhatIfMetric
    whatif: WhatIfMetric
    delta: WhatIfDelta
    sql: str
    ephemeral: Literal[True] = True
    note: str = EXPLORATION_NOTE


class WhatIfNotSupported(ValueError):
    """Raised when a requested binding cannot be explored safely."""


def reconcile_what_if(
    provider: LocalProvider,
    payload: WhatIfRequest,
    period: EvaluationPeriod,
) -> WhatIfResult:
    """Re-execute one copied binding without creating governed state."""
    concept = provider.resolve_concept(payload.term)
    bindings = provider.get_binding_semantics(concept.concept_id)
    binding = _select_binding(bindings, payload.binding_id)
    if binding.time_window_days is None:
        raise WhatIfNotSupported(
            f"Binding {binding.binding_id} has no trailing time window to override."
        )

    baseline = provider.evaluate_binding(binding, period)
    copied_binding = binding.model_copy(
        update={"time_window_days": payload.overrides.time_window_days}
    )
    explored = provider.evaluate_binding(copied_binding, period)

    return WhatIfResult(
        term=concept.canonical_name,
        binding_id=binding.binding_id,
        overrides=payload.overrides,
        baseline=WhatIfMetric(
            entity_count=baseline.entity_count,
            metric_value=baseline.metric_total,
        ),
        whatif=WhatIfMetric(
            entity_count=explored.entity_count,
            metric_value=explored.metric_total,
        ),
        delta=WhatIfDelta(
            entity_count=explored.entity_count - baseline.entity_count,
            metric_value=round(explored.metric_total - baseline.metric_total, 2),
        ),
        sql=explored.executed_sql,
    )


def _select_binding(
    bindings: list[DefinitionBinding],
    requested_id: str,
) -> DefinitionBinding:
    binding = next(
        (item for item in bindings if requested_id in {item.binding_id, item.definition_id}),
        None,
    )
    if binding is None:
        raise WhatIfNotSupported(f"No binding {requested_id!r} belongs to the resolved concept.")
    return binding
