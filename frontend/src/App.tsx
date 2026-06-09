import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchDemoScenarios,
  fetchHealth,
  isUngovernedRefusal,
  reconcileTerm,
  reconcileWhatIf,
  runDemoScenario,
} from "./api";
import { AskConcord } from "./components/AskConcord";
import { DashboardDisagreement } from "./components/DashboardDisagreement";
import { DecoyRuledOut } from "./components/DecoyRuledOut";
import { PortfolioBoard } from "./components/PortfolioBoard";
import { DefinitionDiff } from "./components/DefinitionDiff";
import { EvidencePanel } from "./components/EvidencePanel";
import { ImpactPanel } from "./components/ImpactPanel";
import { NarrationPanel } from "./components/NarrationPanel";
import { ProviderBadge } from "./components/ProviderBadge";
import { ReasoningTimeline } from "./components/ReasoningTimeline";
import { RefusalCard } from "./components/RefusalCard";
import { SemanticPullRequest } from "./components/SemanticPullRequest";
import { TermSearch } from "./components/TermSearch";
import { UngovernedRefusalCard } from "./components/UngovernedRefusalCard";
import type {
  DemoScenario,
  HealthStatus,
  ImpactAssessment,
  ReconciliationCase,
  UngovernedTermRefusal,
  WhatIfResult,
} from "./types";

const SCENARIO_STORIES = [
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

function outcomeTitle(result: ReconciliationCase) {
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
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [selectedId, setSelectedId] = useState("active-customer");
  const [result, setResult] = useState<ReconciliationCase | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refusal, setRefusal] = useState<UngovernedTermRefusal | null>(null);
  const [whatIf, setWhatIf] = useState<WhatIfResult | null>(null);
  const [whatIfBusy, setWhatIfBusy] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const whatIfRequest = useRef(0);

  useEffect(() => {
    let active = true;
    Promise.all([fetchHealth(), fetchDemoScenarios()])
      .then(([healthResponse, scenarioResponse]) => {
        if (!active) {
          return;
        }
        setHealth(healthResponse);
        setScenarios(scenarioResponse);
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
    setRefusal(null);
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
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The deterministic reconciliation run failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  function handleAskAnswer(caseResult: ReconciliationCase) {
    setRefusal(null);
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
    setRefusal(null);
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
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The deterministic reconciliation run failed.",
      );
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

      <main id="top">
        <section className="hero" id="workbench">
          <div className="hero-copy">
            {foundryHosted && (
              <span className="runtime-label">Runtime: Foundry Agent Service</span>
            )}
            <span className="eyebrow">
              <i aria-hidden="true" />
              Semantic reconciliation agent
            </span>
            <h1>
              Settle what the business <em>means</em> before the board meeting.
            </h1>
            <p>
              Concord IQ finds when teams use the same term differently, tests each
              meaning against data, and proposes a governed resolution or refuses one.
            </p>
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
            hostedRuntime={foundryHosted}
            onSelect={(scenarioId) => {
              setSelectedId(scenarioId);
              setResult(null);
              setRefusal(null);
              resetWhatIf();
            }}
            onRun={handleRun}
            onInvestigate={handleInvestigate}
          />
        </section>

        {error && (
          <div className="error-banner" role="alert">
            <strong>Local demo unavailable.</strong>
            <span>{error}</span>
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
            {SCENARIO_STORIES.map((story) => (
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
          <AskConcord onAnswer={handleAskAnswer} busy={busy} setBusy={setBusy} />
        )}
        {!result && <PortfolioBoard onInvestigate={handleInvestigate} busy={busy} />}

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

            <DashboardDisagreement result={result} />
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
                </section>
              </div>
            </div>

            {result.reconciliation_proposal && (
              <SemanticPullRequest
                proposal={result.reconciliation_proposal}
                runId={result.run_id}
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
        <p>
          {foundryHosted
            ? "Foundry Agent Service runtime · replay-grounded proof · cloud enabled"
            : "Deterministic reviewer mode · synthetic data · cloud disabled by default"}
        </p>
        <span>Microsoft Agents League 2026</span>
      </footer>
    </div>
  );
}
