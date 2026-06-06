"""Foundry Agent Service entrypoint for the Concord IQ workflow."""

from __future__ import annotations

import os

from concord.config import Settings
from concord.ms_agent.tools import reconcile_business_term
from concord.ms_agent.workflow import ConcordAgentWorkflow
from concord.providers import create_preferred_cloud_provider


def build_hosted_agent(settings: Settings | None = None):
    """Build a hosted workflow agent after explicit cloud and IQ checks."""
    active_settings = settings or Settings()
    active_settings.require_cloud_access("Foundry Agent Service")
    create_preferred_cloud_provider(active_settings)
    workflow = ConcordAgentWorkflow(
        reconcile_business_term,
        default_provider="auto",
    ).build()
    return workflow.as_agent(
        name="Concord IQ",
        description=(
            "Reconciles conflicting business definitions using governed IQ grounding "
            "and deterministic evidence."
        ),
    )


def main() -> None:
    """Start the optional Foundry responses host."""
    from agent_framework_foundry_hosting import ResponsesHostServer

    port = int(os.environ.get("PORT", "8080"))
    ResponsesHostServer(build_hosted_agent()).run(port=port)


if __name__ == "__main__":
    main()
