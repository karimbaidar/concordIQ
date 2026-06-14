import type { ReconciliationCase } from "../types";

interface DashboardDisagreementProps {
  result: ReconciliationCase;
}

const OWNER_COLORS: Record<string, string> = {
  Finance: "blue",
  Sales: "violet",
  "Customer Success": "teal",
  HR: "blue",
  "Learning & Development": "violet",
  Managers: "teal",
};

function formatMetric(value: number) {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
    style: "currency",
    currency: "USD",
  }).format(value);
}

export function DashboardDisagreement({ result }: DashboardDisagreementProps) {
  const bindings = new Map(
    result.binding_semantics.map((binding) => [binding.binding_id, binding]),
  );

  const governed = result.governed_canonical;
  const learning = result.resolved_concept?.concept_id === "certification_ready";
  const impact = result.impact_assessment;
  const evaluationByOwner = new Map(
    result.execution_results.map((evaluation) => [
      bindings.get(evaluation.binding_id)?.owner,
      evaluation,
    ]),
  );
  const claimedReady = evaluationByOwner.get("HR")?.entity_count;
  const verifiedReady =
    evaluationByOwner.get("Learning & Development")?.entity_count;

  return (
    <section className="dashboard-disagreement" aria-labelledby="dashboard-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Observed dashboard outputs</span>
          <h2 id="dashboard-title">
            {result.resolved_concept?.canonical_name ?? result.request.term}
          </h2>
        </div>
        <span
          className={`verdict-pill ${
            governed ? "verdict-governed" : `verdict-${result.verdict}`
          }`}
        >
          {governed ? `Governed: Canonical v${governed.version}` : result.verdict}
        </span>
      </div>
      <div className="dashboard-metrics">
        {result.execution_results.map((evaluation) => {
          const binding = bindings.get(evaluation.binding_id);
          const owner = binding?.owner ?? evaluation.definition_id;
          return (
            <article className="dashboard-metric" key={evaluation.binding_id}>
              <div className={`owner-mark owner-${OWNER_COLORS[owner] ?? "blue"}`}>
                {owner
                  .split(" ")
                  .map((word) => word[0])
                  .join("")}
              </div>
              <div>
                <span>{owner}</span>
                <strong>{evaluation.entity_count}</strong>
                <small>{learning ? "learners marked ready" : "selected entities"}</small>
              </div>
              <div className="metric-total">
                <span>{learning ? "Exam vouchers represented" : "Metric value"}</span>
                <strong>{formatMetric(evaluation.metric_total)}</strong>
              </div>
            </article>
          );
        })}
      </div>
      {learning && impact && governed && (
        <div className="readiness-summary" aria-label="Certification readiness outcome">
          <div>
            <span>Canonical ready</span>
            <strong>{result.execution_results[0]?.entity_count ?? 0}</strong>
            <small>Canonical v{governed.version} population</small>
          </div>
          <div>
            <span>False-ready learners</span>
            <strong>0</strong>
            <small>Unqualified enterprise views no longer publish</small>
          </div>
          <div className="readiness-risk">
            <span>Exam spend at risk</span>
            <strong>{formatMetric(impact.arr_delta)}</strong>
            <small>Governed canonical execution</small>
          </div>
        </div>
      )}
      {learning && impact && !governed && (
        <div className="readiness-summary" aria-label="Certification readiness outcome">
          <div>
            <span>Claimed ready</span>
            <strong>{claimedReady ?? 0}</strong>
            <small>HR module-completion view</small>
          </div>
          <div>
            <span>Verified ready</span>
            <strong>{verifiedReady ?? 0}</strong>
            <small>L&amp;D modules + latest score</small>
          </div>
          <div className="readiness-risk">
            <span>False-ready learners</span>
            <strong>{impact.false_positive_count ?? 0}</strong>
            <small>Claimed ready but below the verified threshold</small>
          </div>
          <div className="readiness-risk">
            <span>Exam spend at risk</span>
            <strong>{formatMetric(impact.arr_delta)}</strong>
            <small>Synthetic voucher cost</small>
          </div>
        </div>
      )}
    </section>
  );
}
