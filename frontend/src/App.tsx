import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchDemoScenarios,
  fetchHealth,
  fetchLearningScaleProof,
  fetchRuntimeState,
  isUngovernedRefusal,
  ConcordApiError,
  reconcileTerm,
  reconcileWhatIf,
  runCourt,
  runDemoScenario,
  runGovernedRerun,
  selectRuntime,
} from "./api";
import { AskConcord } from "./components/AskConcord";
import { CaseProvenance } from "./components/CaseProvenance";
import { CourtTimeline } from "./components/CourtTimeline";
import { DashboardDisagreement } from "./components/DashboardDisagreement";
import { DecoyRuledOut } from "./components/DecoyRuledOut";
import { PortfolioBoard } from "./components/PortfolioBoard";
import { DefinitionDiff } from "./components/DefinitionDiff";
import { EvidencePanel } from "./components/EvidencePanel";
import { ImpactPanel } from "./components/ImpactPanel";
import { LearningScaleProof } from "./components/LearningScaleProof";
import { MeaningGraph } from "./components/MeaningGraph";
import { NarrationPanel } from "./components/NarrationPanel";
import { ProviderBadge } from "./components/ProviderBadge";
import { ReasoningTimeline } from "./components/ReasoningTimeline";
import { RefusalCard } from "./components/RefusalCard";
import { SemanticPullRequest } from "./components/SemanticPullRequest";
import { TermSearch } from "./components/TermSearch";
import { RuntimeSwitcher } from "./components/RuntimeSwitcher";
import { UngovernedRefusalCard } from "./components/UngovernedRefusalCard";
import type {
  DeliberationTranscript,
  DemoScenario,
  HealthStatus,
  ImpactAssessment,
  LearningScaleProof as LearningScaleProofType,
  ProposalDecisionResult,
  ReconciliationCase,
  RuntimeProfile,
  RuntimeState,
  ScenarioPack,
  UngovernedTermRefusal,
  WhatIfResult,
} from "./types";

const BUSINESS_STORIES = [
  {
    number: "01",
    title: "Detect a real conflict",
    copy: "Execute every definition and prove the populations diverge.",
  },
  {
    number: "02",
    title: "Reject the decoy",
    copy: "Ignore wording differences when the result sets are equal.",
  },
  {
    number: "03",
    title: "Respect governance",
    copy: "Refuse a canonical choice when authority is unresolved.",
  },
];

const LEARNING_STORIES = [
  {
    number: "01",
    title: "Detect false readiness",
    copy: "Execute HR, L&D, and manager definitions over the same learner cohort.",
  },
  {
    number: "02",
    title: "Prove the exposure",
    copy: "Identify false-ready learner IDs and quantify synthetic exam spend at risk.",
  },
  {
    number: "03",
    title: "Gate the definition",
    copy: "Route one evidence-backed readiness definition to the real authority owner.",
  },
];

function outcomeTitle(result: ReconciliationCase) {
  if (result.governed_canonical) {
    return `Governed canonical v${result.governed_canonical.version} in force`;
  }
  if (result.reconciliation_proposal) {
    return "Material conflict confirmed";
  }
  if (result.refusal_reason) {
    return "Conflict confirmed; automatic choice refused";
  }
  return "Apparent conflict ruled out";
}

function rederiveImpact(
  result: ReconciliationCase,
  whatIf: WhatIfResult | null,
): ImpactAssessment | null {
  if (!result.impact_assessment || !whatIf) {
    return result.impact_assessment;
  }
  const evaluations = result.execution_results.map((evaluation) =>
    evaluation.binding_id === whatIf.binding_id
      ? {
          entityCount: whatIf.whatif.entity_count,
          metricTotal: whatIf.whatif.metric_value,
        }
      : {
          entityCount: evaluation.entity_count,
          metricTotal: evaluation.metric_total,
        },
  );
  const counts = evaluations.map((evaluation) => evaluation.entityCount);
  const totals = evaluations.map((evaluation) => evaluation.metricTotal);
  const customerDelta = Math.max(...counts) - Math.min(...counts);
  const metricDelta = Math.round((Math.max(...totals) - Math.min(...totals)) * 100) / 100;
  const consistent = customerDelta === 0 && metricDelta === 0;
  const highImpact = customerDelta >= 10 || metricDelta >= 1_000_000;

  return {
    ...result.impact_assessment,
    rank: consistent ? 0 : 1,
    severity: consistent ? "low" : highImpact ? "high" : "medium",
    customer_count_delta: customerDelta,
    arr_delta: metricDelta,
    decision_criticality: consistent ? "low" : "high",
  };
}

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [runtime, setRuntime] = useState<RuntimeState | null>(null);
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [result, setResult] = useState<ReconciliationCase | null>(null);
  const [court, setCourt] = useState<DeliberationTranscript | null>(null);
  const [courtBusy, setCourtBusy] = useState(false);
  const [courtError, setCourtError] = useState<string | null>(null);
  const [learningScale, setLearningScale] = useState<LearningScaleProofType | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorRecovery, setErrorRecovery] = useState<{
    profile: RuntimeProfile;
    label: string;
  } | null>(null);
  const [refusal, setRefusal] = useState<UngovernedTermRefusal | null>(null);
  const [whatIf, setWhatIf] = useState<WhatIfResult | null>(null);
  const [whatIfBusy, setWhatIfBusy] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const [mergedDecision, setMergedDecision] =
    useState<ProposalDecisionResult | null>(null);
  const whatIfRequest = useRef(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetchRuntimeState(),
      fetchHealth(),
      fetchDemoScenarios(),
      fetchLearningScaleProof().catch(() => null),
    ])
      .then(([runtimeResponse, healthResponse, scenarioResponse, scaleResponse]) => {
        if (!active) {
          return;
        }
        setRuntime(runtimeResponse);
        setHealth(healthResponse);
        setScenarios(scenarioResponse);
        setLearningScale(scaleResponse);
        setSelectedId((currentId) =>
          scenarioResponse.some((item) => item.scenario_id === currentId)
            ? currentId
            : scenarioResponse[0]?.scenario_id ?? currentId,
        );
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to connect to the local Concord IQ API.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedScenario = useMemo(
    () => scenarios.find((scenario) => scenario.scenario_id === selectedId),
    [scenarios, selectedId],
  );
  const foundryHosted =
    health?.provider_mode === "foundry_hosted" ||
    result?.context_packet?.provider_metadata.mode === "foundry_hosted";
  const learningMode =
    runtime?.scenario_pack === "learning" ||
    health?.scenario_pack === "learning" ||
    scenarios[0]?.scenario_id === "certification-ready";
  const stories = learningMode ? LEARNING_STORIES : BUSINESS_STORIES;
  const runtimeSummary =
    runtime?.runtime_profile === "foundry_live"
      ? "Foundry Agent Service live · verified Fabric replay · cloud enabled"
      : runtime?.runtime_profile === "fabric_live"
        ? "Fabric IQ live grounding · deterministic verdict · cloud enabled"
        : runtime?.runtime_profile === "fabric_replay"
          ? "Verified Fabric IQ replay · deterministic verdict · no cloud call"
          : "Local deterministic reviewer mode · synthetic data · no cloud call";
  const whatIfEnabled = result?.context_packet?.provider_metadata.mode === "local";
  const displayedImpact = useMemo(
    () => (result ? rederiveImpact(result, whatIf) : null),
    [result, whatIf],
  );

  const resetWhatIf = useCallback(() => {
    whatIfRequest.current += 1;
    setWhatIf(null);
    setWhatIfBusy(false);
    setWhatIfError(null);
  }, []);

  const showRequestError = useCallback(
    (requestError: unknown, fallback: string) => {
      setError(requestError instanceof Error ? requestError.message : fallback);
      setErrorRecovery(
        requestError instanceof ConcordApiError && requestError.recoveryProfile
          ? {
              profile: requestError.recoveryProfile,
              label: requestError.recoveryLabel ?? "Use verified replay",
            }
          : null,
      );
    },
    [],
  );

  const handleWhatIf = useCallback(
    async (bindingId: string, timeWindowDays: number) => {
      if (!result) {
        return;
      }
      const requestId = whatIfRequest.current + 1;
      whatIfRequest.current = requestId;
      setWhatIfBusy(true);
      setWhatIfError(null);
      try {
        const response = await reconcileWhatIf(
          result.resolved_concept?.canonical_name ?? result.request.term,
          bindingId,
          timeWindowDays,
        );
        if (whatIfRequest.current === requestId) {
          setWhatIf(response);
        }
      } catch (requestError) {
        if (whatIfRequest.current === requestId) {
          setWhatIfError(
            requestError instanceof Error
              ? requestError.message
              : "The deterministic what-if run failed.",
          );
        }
      } finally {
        if (whatIfRequest.current === requestId) {
          setWhatIfBusy(false);
        }
      }
    },
    [result],
  );

  async function handleRun() {
    if (!selectedScenario) {
      return;
    }
    setBusy(true);
    setError(null);
    setErrorRecovery(null);
    setRefusal(null);
    setMergedDecision(null);
    setCourt(null);
    setCourtError(null);
    resetWhatIf();
    try {
      const caseResult = await runDemoScenario(selectedScenario.scenario_id);
      setResult(caseResult);
      requestAnimationFrame(() => {
        document.getElementById("case-result")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    } catch (requestError) {
      showRequestError(requestError, "The deterministic reconciliation run failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleConvene() {
    if (!result) {
      return;
    }
    setCourtBusy(true);
    setCourtError(null);
    try {
      setCourt(await runCourt(result.run_id));
    } catch (requestError) {
      setCourtError(
        requestError instanceof Error
          ? requestError.message
          : "The Semantic Court could not convene.",
      );
    } finally {
      setCourtBusy(false);
    }
  }

  async function handleRuntimeSelect(
    scenarioPack: ScenarioPack,
    runtimeProfile: RuntimeProfile,
  ) {
    setBusy(true);
    setError(null);
    setErrorRecovery(null);
    setResult(null);
    setRefusal(null);
    setMergedDecision(null);
    setCourt(null);
    setCourtError(null);
    resetWhatIf();
    try {
      const selected = await selectRuntime(scenarioPack, runtimeProfile);
      const [healthResponse, scenarioResponse] = await Promise.all([
        fetchHealth(),
        fetchDemoScenarios(),
      ]);
      setRuntime(selected);
      setHealth(healthResponse);
      setScenarios(scenarioResponse);
      setSelectedId(scenarioResponse[0]?.scenario_id ?? "");
    } catch (requestError) {
      showRequestError(requestError, "Unable to switch the Concord IQ runtime.");
    } finally {
      setBusy(false);
    }
  }

  function handleAskAnswer(caseResult: ReconciliationCase) {
    setRefusal(null);
    setMergedDecision(null);
    setCourt(null);
    setCourtError(null);
    resetWhatIf();
    setResult(caseResult);
    requestAnimationFrame(() => {
      document.getElementById("case-result")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  async function handleInvestigate(term: string) {
    setBusy(true);
    setError(null);
    setErrorRecovery(null);
    setRefusal(null);
    setMergedDecision(null);
    setCourt(null);
    setCourtError(null);
    resetWhatIf();
    try {
      const outcome = await reconcileTerm(term);
      if (isUngovernedRefusal(outcome)) {
        setResult(null);
        setRefusal(outcome);
        requestAnimationFrame(() => {
          document.getElementById("ungoverned-refusal")?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        });
        return;
      }
      setResult(outcome);
      requestAnimationFrame(() => {
        document.getElementById("case-result")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    } catch (requestError) {
      showRequestError(requestError, "The deterministic reconciliation run failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleGovernedRerun(runId: string) {
    setBusy(true);
    setError(null);
    setErrorRecovery(null);
    resetWhatIf();
    setCourt(null);
    setCourtError(null);
    try {
      const outcome = await runGovernedRerun(runId);
      setRefusal(null);
      setResult(outcome);
      setMergedDecision(null);
      requestAnimationFrame(() => {
        document.getElementById("case-result")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    } catch (requestError) {
      const failure =
        requestError instanceof Error
          ? requestError
          : new Error("The governed reconciliation re-run failed.");
      setError(failure.message);
      setErrorRecovery(null);
      throw failure;
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Concord IQ home">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span>
            <strong>Concord</strong>
            <em>IQ</em>
          </span>
        </a>
        <nav aria-label="Product sections">
          <a href="#workbench">Workbench</a>
          <a href="#reasoning">Reasoning</a>
          <a href="#evidence">Evidence</a>
        </nav>
        <ProviderBadge health={health} result={result} />
      </header>

      <RuntimeSwitcher
        runtime={runtime}
        busy={busy}
        onSelect={handleRuntimeSelect}
      />

      <main id="top">
        <section className="hero" id="workbench">
          <div className="hero-copy">
            {foundryHosted && (
              <span className="runtime-label">Selected runtime: Foundry Agent Service</span>
            )}
            <span className="eyebrow">
              <i aria-hidden="true" />
              {learningMode
                ? "Enterprise learning reconciliation"
                : "Semantic reconciliation agent"}
            </span>
            {learningMode ? (
              <>
                <h1>
                  The <em>False Readiness Firewall</em> for enterprise certification.
                </h1>
                <p>
                  HR, Learning &amp; Development, and managers define readiness
                  differently. Concord IQ proves the disagreement before dashboards,
                  exam budget, or team readiness are trusted.
                </p>
              </>
            ) : (
              <>
                <h1>
                  Settle what the business <em>means</em> before the board meeting.
                </h1>
                <p>
                  Concord IQ finds when teams use the same term differently, tests each
                  meaning against data, and proposes a governed resolution or refuses one.
                </p>
              </>
            )}
            <div className="trust-row">
              <span>Deterministic SQL</span>
              <span>Typed evidence</span>
              <span>Human authority</span>
            </div>
          </div>
          <TermSearch
            scenarios={scenarios}
            selectedId={selectedId}
            busy={busy}
            runtimeProfile={runtime?.runtime_profile}
            onSelect={(scenarioId) => {
              setSelectedId(scenarioId);
              setResult(null);
              setRefusal(null);
              setMergedDecision(null);
              resetWhatIf();
            }}
            onRun={handleRun}
            onInvestigate={handleInvestigate}
          />
        </section>

        {error && (
          <div className="error-banner" role="alert">
            <div>
              <strong>Concord IQ request unavailable.</strong>
              <span>{error}</span>
            </div>
            {errorRecovery && runtime && (
              <button
                type="button"
                className="error-recovery-button"
                disabled={busy}
                onClick={() =>
                  handleRuntimeSelect(runtime.scenario_pack, errorRecovery.profile)
                }
              >
                {errorRecovery.label}
              </button>
            )}
          </div>
        )}

        {refusal && !result && (
          <div id="ungoverned-refusal">
            <UngovernedRefusalCard
              refusal={refusal}
              busy={busy}
              onInvestigate={handleInvestigate}
            />
          </div>
        )}

        {!result && (
          <section className="story-strip" aria-label="Demo flow">
            {stories.map((story) => (
              <article key={story.number}>
                <span>{story.number}</span>
                <div>
                  <strong>{story.title}</strong>
                  <p>{story.copy}</p>
                </div>
              </article>
            ))}
          </section>
        )}

        {!result && (
          <AskConcord
            onAnswer={handleAskAnswer}
            busy={busy}
            setBusy={setBusy}
            scenarioPack={learningMode ? "learning" : "business"}
          />
        )}
        {!result && (
          <PortfolioBoard
            key={`${runtime?.scenario_pack}:${runtime?.runtime_profile}`}
            onInvestigate={handleInvestigate}
            busy={busy}
          />
        )}

        {result && (
          <div className="result-area" id="case-result">
            <section className={`outcome-banner outcome-${result.verdict}`}>
              <div>
                <span>Verified outcome</span>
                <h2>{outcomeTitle(result)}</h2>
              </div>
              <div className="outcome-facts">
                <span aria-label={`${result.evidence.length} evidence records`}>
                  <strong>{result.evidence.length}</strong>
                  evidence records
                </span>
                <span>
                  <strong>{result.verifier_report?.passed ? "Passed" : "Review"}</strong>
                  skeptical verifier
                </span>
                <span>
                  <strong>{result.context_packet?.provider_metadata.mode ?? "local"}</strong>
                  provider mode
                </span>
              </div>
            </section>
            <CaseProvenance
              result={result}
              runtimeProfile={runtime?.runtime_profile}
            />

            <MeaningGraph
              result={result}
              whatIf={whatIf}
              impact={displayedImpact}
              mergedDecision={mergedDecision}
            />
            <DashboardDisagreement result={result} />
            {learningMode && learningScale && (
              <LearningScaleProof proof={learningScale} />
            )}
            <DefinitionDiff
              result={result}
              whatIf={whatIf}
              whatIfBusy={whatIfBusy}
              whatIfError={whatIfError}
              whatIfEnabled={whatIfEnabled}
              onWhatIf={handleWhatIf}
              onResetWhatIf={resetWhatIf}
            />

            <div className="analysis-grid" id="reasoning">
              <ReasoningTimeline result={result} />
              <div className="analysis-sidebar">
                {displayedImpact && (
                  <ImpactPanel impact={displayedImpact} exploring={Boolean(whatIf)} />
                )}
                <section className="surface authority-panel">
                  <span className="section-kicker">Decision authority</span>
                  <h2>{result.authority_assessment?.owner ?? "No single owner"}</h2>
                  <p>{result.authority_assessment?.rationale}</p>
                  <span className="authority-status">
                    {result.authority_assessment?.status ?? "missing"}
                  </span>
                  {result.authority_assessment?.advisory_grounding && (
                    <div className="authority-grounding">
                      <span className="grounding-kicker">Governance grounding · advisory</span>
                      <p>{result.authority_assessment.advisory_grounding.note}</p>
                      <span className="grounding-source">
                        {result.authority_assessment.advisory_grounding.source} ·{" "}
                        {result.authority_assessment.advisory_grounding.agrees_with_rule
                          ? "corroborates the deterministic rule"
                          : "differs — the deterministic rule still decides"}
                      </span>
                    </div>
                  )}
                </section>
              </div>
            </div>

            <section className="surface court-convene">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">
                    Phase 2 · separate Microsoft Agent Framework workflow
                  </span>
                  <h2>Convene the Semantic Court over this frozen run</h2>
                </div>
                <button
                  type="button"
                  className="court-button"
                  onClick={handleConvene}
                  disabled={courtBusy}
                >
                  {courtBusy ? "Convening…" : "Convene the court"}
                </button>
              </div>
              <p className="court-blurb">
                The evidence workflow is complete. Court agents now argue, investigate, and
                cross-examine the stored case while the engine-owned verdict remains immutable.
              </p>
              <p className="court-guarantee">
                No SQL rerun. No new verdict. No duplicate proposal.
              </p>
              {courtError && <p className="error-text">{courtError}</p>}
            </section>
            {court && <CourtTimeline transcript={court} />}

            {result.reconciliation_proposal && (
              <SemanticPullRequest
                proposal={result.reconciliation_proposal}
                runId={result.run_id}
                onRerun={() => handleGovernedRerun(result.run_id)}
                onDecision={(decision) =>
                  setMergedDecision(decision.status === "approved" ? decision : null)
                }
              />
            )}
            {result.refusal_reason && result.authority_assessment && (
              <RefusalCard
                reason={result.refusal_reason}
                authority={result.authority_assessment}
              />
            )}
            {result.verdict === "consistent" && <DecoyRuledOut result={result} />}

            <NarrationPanel narrations={result.narrations} />

            <div id="evidence">
              <EvidencePanel result={result} />
            </div>
          </div>
        )}
      </main>

      <footer className="site-footer">
        <span>Concord IQ</span>
        <p>{runtimeSummary}</p>
        <span>Microsoft Agents League 2026</span>
      </footer>
    </div>
  );
}
