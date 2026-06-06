import type { ReconciliationCase } from "../types";

interface DashboardDisagreementProps {
  result: ReconciliationCase;
}

const OWNER_COLORS: Record<string, string> = {
  Finance: "blue",
  Sales: "violet",
  "Customer Success": "teal",
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

  return (
    <section className="dashboard-disagreement" aria-labelledby="dashboard-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Observed dashboard outputs</span>
          <h2 id="dashboard-title">
            {result.resolved_concept?.canonical_name ?? result.request.term}
          </h2>
        </div>
        <span className={`verdict-pill verdict-${result.verdict}`}>{result.verdict}</span>
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
                <small>selected entities</small>
              </div>
              <div className="metric-total">
                <span>Metric value</span>
                <strong>{formatMetric(evaluation.metric_total)}</strong>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
