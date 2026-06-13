"""Work IQ provider boundary (Microsoft 365 Copilot Retrieval)."""

from typing import TYPE_CHECKING, Any

from concord.config import Settings
from concord.providers.base import ProviderMode, ProviderNotConfigured
from concord.providers.cloud import JsonTransport
from concord.providers.cloud_snapshot import CloudSnapshotProvider
from concord.providers.replay_schema import (
    ReplayScenarioSnapshot,
    SnapshotNotFound,
    find_snapshot,
    response_shape,
    snapshot_provider_scenario,
)

if TYPE_CHECKING:
    from concord.providers.local import LocalProvider

ARTIFACT_PROOF_MODE = "work_iq_artifact_proof_with_deterministic_snapshot"
ARTIFACT_SNAPSHOT_SOURCE = "LocalProvider synthetic snapshot"
MINIMUM_ARTIFACTS = 2


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _matching_artifacts(payload: dict[str, Any], term: str) -> list[str]:
    """Distinct M365 / Power BI artifacts whose text defines the requested metric.

    Parses a Microsoft 365 Copilot Retrieval ``retrievalHits`` response. A hit is a
    "defining artifact" when its passage text references the metric by name. Two or
    more distinct artifacts that define the same metric are the Work IQ proof that
    the conflict comes from real org content rather than a seed.
    """
    sought = _normalize(term)
    hits = payload.get("retrievalHits")
    refs: list[str] = []
    if not isinstance(hits, list):
        return refs
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        web_url = str(hit.get("webUrl", "")).strip()
        if not web_url or web_url in refs:
            continue
        texts = [web_url]
        extracts = hit.get("extracts")
        if isinstance(extracts, list):
            texts.extend(str(item.get("text", "")) for item in extracts if isinstance(item, dict))
        if sought in _normalize(" ".join(texts)):
            refs.append(web_url)
    return refs


class WorkIQProvider(CloudSnapshotProvider):
    """Microsoft 365 Work IQ (Copilot Retrieval) adapter, fail-closed.

    Two honest modes, mirroring Fabric IQ:

    * **Full snapshot** — if Work IQ retrieval returns a complete Concord IQ
      scenario snapshot, it is used exactly as returned.
    * **Artifact proof** — if retrieval returns >= 2 distinct M365 / Power BI
      artifacts that define the same metric, Work IQ is recorded as the real
      org-artifact proof and the deterministic LocalProvider snapshot supplies the
      SQL/evidence (transparently labelled). Connectivity-only responses (fewer than
      two defining artifacts) are rejected.

    Work IQ is **not** marked "verified" until a real sanitized capture from a tenant
    exists; the guarded adapter and injected-transport tests stand in for that.
    """

    name = "WorkIQProvider"
    mode = ProviderMode.WORK_IQ

    def __init__(
        self,
        settings: Settings,
        *,
        transport: JsonTransport | None = None,
        local_provider: "LocalProvider | None" = None,
    ) -> None:
        super().__init__(settings, transport=transport)
        self._local_provider = local_provider
        self._artifact_proofs: dict[str, dict[str, Any]] = {}

    @property
    def artifact_proofs(self) -> dict[str, dict[str, Any]]:
        return dict(self._artifact_proofs)

    def _headers(self) -> dict[str, str]:
        if not self.settings.work_iq_access_token:
            raise ProviderNotConfigured("WorkIQProvider requires WORK_IQ_ACCESS_TOKEN.")
        return {
            "Authorization": f"Bearer {self.settings.work_iq_access_token.get_secret_value()}",
            "Content-Type": "application/json",
        }

    def _retrieve_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        endpoint = self.settings.work_iq_endpoint
        if not endpoint:
            raise ProviderNotConfigured("WorkIQProvider requires WORK_IQ_ENDPOINT.")
        body: dict[str, Any] = {
            "queryString": (
                f"How is '{term}' defined across our Power BI reports, finance models, "
                "and sales operating documents? Return each report's exact definition."
            ),
            "dataSource": self.settings.work_iq_data_source,
            "maximumNumberOfResults": 25,
        }
        result = self.client.request("POST", endpoint, headers=self._headers(), body=body)
        # Mode 1: Work IQ returned a complete Concord IQ scenario snapshot.
        try:
            return find_snapshot(result.payload)
        except SnapshotNotFound:
            pass
        # Mode 2: >= 2 real org artifacts define the metric (the work-artifact proof).
        artifacts = _matching_artifacts(result.payload, term)
        if len(artifacts) >= MINIMUM_ARTIFACTS:
            return self._record_artifact_proof(term, artifacts, result.payload)
        raise ProviderNotConfigured(
            f"Work IQ returned fewer than {MINIMUM_ARTIFACTS} artifacts defining {term!r}. "
            "Connectivity-only responses are rejected; a real conflict needs at least two "
            "org artifacts that define the same metric."
        )

    def _record_artifact_proof(
        self,
        term: str,
        artifacts: list[str],
        response: dict[str, Any],
    ) -> ReplayScenarioSnapshot:
        snapshot = self._materialize_local_snapshot(term)
        self._artifact_proofs[term] = {
            "matched_term": term,
            "artifact_count": len(artifacts),
            "artifact_refs": tuple(artifacts),
            "response_shape": response_shape(response),
        }
        return snapshot

    def _materialize_local_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        """Build the deterministic LocalProvider snapshot for a proven term."""
        from concord.demo import demo_scenarios_for_pack
        from concord.providers.local import LocalProvider

        scenario_pack = (
            self._local_provider.scenario_pack
            if self._local_provider is not None
            else self.settings.scenario_pack
        )
        scenarios = demo_scenarios_for_pack(scenario_pack)
        scenario = next((item for item in scenarios if item.term == term), None)
        if scenario is None:
            raise ProviderNotConfigured(
                f"No deterministic synthetic scenario is registered for {term!r}."
            )
        provider = self._local_provider or LocalProvider.for_scenario_pack(
            scenario_pack,
            duckdb_path=self.settings.duckdb_path,
        )
        return snapshot_provider_scenario(provider, scenario)
