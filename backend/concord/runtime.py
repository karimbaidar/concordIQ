"""Single-user demo runtime selection for scenario packs and proof sources."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine

from concord.config import ScenarioPack, Settings
from concord.llm import LLMProvider, create_llm_provider
from concord.ms_agent import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationCase
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import (
    FoundryHostedProvider,
    GroundingProvider,
    ProviderMode,
    create_provider,
    fabric_iq_is_configured,
    foundry_hosted_is_configured,
)
from concord.storage.repositories import ReconciliationRepository


class RuntimeProfile(StrEnum):
    """Reviewer-visible execution and grounding profiles."""

    FABRIC_LIVE = "fabric_live"
    FABRIC_REPLAY = "fabric_replay"
    FOUNDRY_LIVE = "foundry_live"
    LOCAL = "local"


class ScenarioPackOption(BaseModel):
    """One reviewed semantic system that the UI may select."""

    model_config = ConfigDict(frozen=True)

    id: ScenarioPack
    label: str
    enabled: bool
    detail: str


class RuntimeProfileOption(BaseModel):
    """One truthful runtime/grounding combination exposed to reviewers."""

    model_config = ConfigDict(frozen=True)

    id: RuntimeProfile
    label: str
    available: bool
    cloud: bool
    detail: str
    supported_packs: tuple[ScenarioPack, ...]


class RuntimeState(BaseModel):
    """Current runtime selection plus all switchable options."""

    model_config = ConfigDict(frozen=True)

    scenario_pack: ScenarioPack
    runtime_profile: RuntimeProfile
    switching_enabled: bool
    scenario_packs: tuple[ScenarioPackOption, ...]
    runtime_profiles: tuple[RuntimeProfileOption, ...]


@dataclass(slots=True)
class RuntimeContext:
    """Dependencies for one active runtime profile."""

    settings: Settings
    runner: ReconciliationRunner | None
    workflow: ConcordAgentWorkflow | None
    hosted: FoundryHostedProvider | None


class RuntimeSelectionError(ValueError):
    """Raised when a disabled or unavailable runtime selection is requested."""


@dataclass(slots=True)
class CachedCase:
    """One immutable reviewer-visible case and the semantic system that produced it."""

    case: ReconciliationCase
    scenario_pack: ScenarioPack


class RuntimeManager:
    """Own the active provider for the single-user reviewer application.

    Switching is deliberately process-local. It changes no governed definitions,
    writes no credentials, and is intended for one presenter operating one demo UI.
    """

    case_cache_limit = 32

    def __init__(
        self,
        settings: Settings,
        *,
        engine: Engine,
        provider: GroundingProvider | None = None,
        foundry_hosted_provider: FoundryHostedProvider | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.base_settings = settings
        self.engine = engine
        self.repository = ReconciliationRepository(engine)
        self._llm_provider = llm_provider
        self._lock = Lock()
        self._cases: OrderedDict[UUID, CachedCase] = OrderedDict()
        self._fixed = provider is not None or foundry_hosted_provider is not None

        if provider is not None:
            pack = ScenarioPack(getattr(provider, "scenario_pack", settings.scenario_pack))
            profile = self._profile_for_provider(provider.mode)
            self.context = self._runner_context(
                settings.model_copy(
                    update={"provider": provider.mode.value, "scenario_pack": pack}
                ),
                provider,
            )
            self.scenario_pack = pack
            self.runtime_profile = profile
        elif foundry_hosted_provider is not None:
            pack = foundry_hosted_provider.scenario_pack
            self.context = RuntimeContext(
                settings=foundry_hosted_provider.settings,
                runner=None,
                workflow=None,
                hosted=foundry_hosted_provider,
            )
            self.scenario_pack = pack
            self.runtime_profile = RuntimeProfile.FOUNDRY_LIVE
        else:
            self.scenario_pack = settings.scenario_pack
            self.runtime_profile = (
                RuntimeProfile(settings.default_runtime_profile)
                if settings.runtime_switching
                else self._profile_for_provider(ProviderMode(settings.provider))
            )
            self.context = self._build_context(self.runtime_profile, self.scenario_pack)

    @staticmethod
    def _profile_for_provider(mode: ProviderMode) -> RuntimeProfile:
        mapping = {
            ProviderMode.FABRIC_IQ: RuntimeProfile.FABRIC_LIVE,
            ProviderMode.REPLAY: RuntimeProfile.FABRIC_REPLAY,
            ProviderMode.FOUNDRY_HOSTED: RuntimeProfile.FOUNDRY_LIVE,
            ProviderMode.LOCAL: RuntimeProfile.LOCAL,
        }
        return mapping.get(mode, RuntimeProfile.LOCAL)

    def initialize(self) -> None:
        """Initialize shared registry storage once for all in-process profiles."""
        self.repository.initialize()

    def remember_case(
        self,
        case: ReconciliationCase,
        *,
        import_to_registry: bool = False,
    ) -> ReconciliationCase:
        """Cache one completed verified case without trusting mutable caller state."""
        if (
            case.verdict == "incomplete"
            or case.verification_status != "passed"
            or case.verifier_report is None
            or not case.verifier_report.passed
        ):
            raise ValueError("Only completed verifier-approved cases may enter the run cache.")
        if import_to_registry:
            self.repository.import_verified_case(case)
        frozen = case.model_copy(deep=True)
        with self._lock:
            self._cases[case.run_id] = CachedCase(
                case=frozen,
                scenario_pack=self.scenario_pack,
            )
            self._cases.move_to_end(case.run_id)
            while len(self._cases) > self.case_cache_limit:
                self._cases.popitem(last=False)
        return case

    def cached_case(self, run_id: UUID) -> CachedCase | None:
        """Return a defensive copy of a cached case, refreshing its LRU position."""
        with self._lock:
            cached = self._cases.get(run_id)
            if cached is None:
                return None
            self._cases.move_to_end(run_id)
            return CachedCase(
                case=cached.case.model_copy(deep=True),
                scenario_pack=cached.scenario_pack,
            )

    def local_workflow(self, pack: ScenarioPack) -> ConcordAgentWorkflow:
        """Build a cloud-free workflow over the shared governed registry."""
        settings = self.base_settings.model_copy(
            update={
                "provider": ProviderMode.LOCAL.value,
                "scenario_pack": pack,
                "allow_cloud": False,
                "max_cloud_calls": 0,
            }
        )
        provider = create_provider(settings)
        workflow = self._runner_context(settings, provider).workflow
        if workflow is None:
            raise RuntimeError("Local deterministic workflow could not be constructed.")
        return workflow

    def _replay_path(self, pack: ScenarioPack):
        if pack is ScenarioPack.LEARNING:
            return self.base_settings.learning_replay_artifact_path
        return self.base_settings.business_replay_artifact_path

    def _runner_context(
        self,
        settings: Settings,
        provider: GroundingProvider,
    ) -> RuntimeContext:
        llm_provider = self._llm_provider or create_llm_provider(settings)
        runner = ReconciliationRunner(
            provider=provider,
            repository=self.repository,
            settings=settings,
            llm_provider=llm_provider,
        )
        return RuntimeContext(
            settings=settings,
            runner=runner,
            workflow=ConcordAgentWorkflow.from_runner(runner),
            hosted=None,
        )

    def _build_context(
        self,
        profile: RuntimeProfile,
        pack: ScenarioPack,
    ) -> RuntimeContext:
        if self.base_settings.runtime_switching:
            self._validate_selection(profile, pack)
        updates: dict[str, object] = {"scenario_pack": pack}
        if profile is RuntimeProfile.FABRIC_LIVE:
            updates["provider"] = ProviderMode.FABRIC_IQ.value
        elif profile is RuntimeProfile.FABRIC_REPLAY:
            updates.update(
                {
                    "provider": ProviderMode.REPLAY.value,
                    "replay_artifact_path": self._replay_path(pack),
                    "allow_cloud": False,
                    "max_cloud_calls": 0,
                }
            )
        elif profile is RuntimeProfile.FOUNDRY_LIVE:
            updates["provider"] = ProviderMode.FOUNDRY_HOSTED.value
        else:
            updates.update(
                {
                    "provider": ProviderMode.LOCAL.value,
                    "allow_cloud": False,
                    "max_cloud_calls": 0,
                }
            )
        settings = self.base_settings.model_copy(update=updates)

        if profile is RuntimeProfile.FOUNDRY_LIVE:
            return RuntimeContext(
                settings=settings,
                runner=None,
                workflow=None,
                hosted=FoundryHostedProvider(settings),
            )
        return self._runner_context(settings, create_provider(settings))

    def _pack_enabled(self, pack: ScenarioPack) -> bool:
        if not self.base_settings.runtime_switching:
            return True
        return pack is ScenarioPack.LEARNING or self.base_settings.enable_business

    def _profile_available(
        self,
        profile: RuntimeProfile,
        pack: ScenarioPack,
    ) -> bool:
        if not self._pack_enabled(pack):
            return False
        if profile is RuntimeProfile.FABRIC_LIVE:
            return pack is ScenarioPack.LEARNING and fabric_iq_is_configured(self.base_settings)
        if profile is RuntimeProfile.FABRIC_REPLAY:
            return self._replay_path(pack).exists()
        if profile is RuntimeProfile.FOUNDRY_LIVE:
            return pack is ScenarioPack.LEARNING and foundry_hosted_is_configured(
                self.base_settings
            )
        return True

    def _validate_selection(
        self,
        profile: RuntimeProfile,
        pack: ScenarioPack,
    ) -> None:
        if not self._pack_enabled(pack):
            raise RuntimeSelectionError(
                "Business scenarios are disabled. Set CONCORD_ENABLE_BUSINESS=true "
                "in .env and restart Concord IQ to enable them."
            )
        if not self._profile_available(profile, pack):
            raise RuntimeSelectionError(
                f"Runtime profile {profile.value!r} is not available for {pack.value!r}."
            )

    def activate(
        self,
        profile: RuntimeProfile,
        pack: ScenarioPack,
    ) -> RuntimeState:
        """Activate one validated profile without persisting the selection."""
        if self._fixed or not self.base_settings.runtime_switching:
            raise RuntimeSelectionError("Runtime switching is disabled for this process.")
        with self._lock:
            context = self._build_context(profile, pack)
            self.context = context
            self.runtime_profile = profile
            self.scenario_pack = pack
        return self.state()

    def state(self) -> RuntimeState:
        """Return current selection and honest availability metadata."""
        packs = (
            ScenarioPackOption(
                id=ScenarioPack.LEARNING,
                label="Learning",
                enabled=True,
                detail="Certification Ready governance and false-readiness proof.",
            ),
            ScenarioPackOption(
                id=ScenarioPack.BUSINESS,
                label="Business",
                enabled=(
                    self.base_settings.enable_business
                    or (
                        not self.base_settings.runtime_switching
                        and self.scenario_pack is ScenarioPack.BUSINESS
                    )
                ),
                detail=(
                    "Business metric governance pack."
                    if self.base_settings.enable_business
                    else "Disabled by CONCORD_ENABLE_BUSINESS=false."
                ),
            ),
        )
        profile_metadata = {
            RuntimeProfile.FABRIC_LIVE: (
                "Fabric IQ Live",
                True,
                (
                    "Live Fabric ontology grounding; deterministic SQL still owns the verdict."
                    if self._profile_available(RuntimeProfile.FABRIC_LIVE, self.scenario_pack)
                    else "Unavailable until Fabric endpoint credentials and an active capacity "
                    "are provided. Use the verified Fabric IQ Replay meanwhile."
                ),
                (ScenarioPack.LEARNING,),
            ),
            RuntimeProfile.FABRIC_REPLAY: (
                "Fabric IQ Replay",
                False,
                "Verified sanitized Fabric capture; no cloud call.",
                (ScenarioPack.LEARNING, ScenarioPack.BUSINESS),
            ),
            RuntimeProfile.FOUNDRY_LIVE: (
                "Foundry Agent Service Live",
                True,
                (
                    "Live hosted Agent Framework runtime over the verified learning replay."
                    if self._profile_available(RuntimeProfile.FOUNDRY_LIVE, self.scenario_pack)
                    else "Unavailable until Foundry endpoint credentials are provided. "
                    "Use the verified Fabric IQ Replay meanwhile."
                ),
                (ScenarioPack.LEARNING,),
            ),
            RuntimeProfile.LOCAL: (
                "Local Deterministic",
                False,
                "Cloud-free synthetic fallback for development and tests.",
                (ScenarioPack.LEARNING, ScenarioPack.BUSINESS),
            ),
        }
        profiles = tuple(
            RuntimeProfileOption(
                id=profile,
                label=metadata[0],
                available=self._profile_available(profile, self.scenario_pack),
                cloud=metadata[1],
                detail=metadata[2],
                supported_packs=metadata[3],
            )
            for profile, metadata in profile_metadata.items()
        )
        return RuntimeState(
            scenario_pack=self.scenario_pack,
            runtime_profile=self.runtime_profile,
            switching_enabled=(self.base_settings.runtime_switching and not self._fixed),
            scenario_packs=packs,
            runtime_profiles=profiles,
        )
