"""Persist verified casefiles and audit timelines."""

from dataclasses import dataclass
from uuid import UUID

from concord.orchestration.casefile import ReconciliationCase
from concord.storage.repositories import ReconciliationRepository


@dataclass(frozen=True, slots=True)
class AuditAgent:
    """Write the final typed case to PostgreSQL."""

    repository: ReconciliationRepository

    def run(self, case: ReconciliationCase) -> UUID:
        return self.repository.save(case)
