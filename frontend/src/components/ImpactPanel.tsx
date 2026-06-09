import type { ImpactAssessment } from "../types";

interface ImpactPanelProps {
  impact: ImpactAssessment;
  exploring?: boolean;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function ImpactPanel({ impact, exploring = false }: ImpactPanelProps) {
  return (
    <section
      className={`surface impact-panel${exploring ? " is-exploring" : ""}`}
      aria-labelledby="impact-title"
    >
      <div className="section-heading">
        <div>
          <span className="section-kicker">Materiality</span>
          <h2 id="impact-title">Business impact</h2>
        </div>
        <div className="impact-badges">
          {exploring && <span className="exploration-chip">Exploration</span>}
          <span className={`severity-badge severity-${impact.severity}`}>
            {impact.severity} impact
          </span>
        </div>
      </div>
      <div className="impact-primary">
        <div>
          <strong className="rederived-value" key={impact.customer_count_delta}>
            {impact.customer_count_delta}
          </strong>
          <span>customer delta</span>
        </div>
        <div>
          <strong className="rederived-value" key={impact.arr_delta}>
            {formatCurrency(impact.arr_delta)}
          </strong>
          <span>metric delta</span>
        </div>
      </div>
      <div className="impact-details">
        <div>
          <span>Rank</span>
          <strong>{impact.rank === 0 ? "No conflict" : `#${impact.rank}`}</strong>
        </div>
        <div>
          <span>Reports affected</span>
          <strong>{impact.reports_affected}</strong>
        </div>
        <div>
          <span>Decision criticality</span>
          <strong>{impact.decision_criticality}</strong>
        </div>
      </div>
      <div className="business-units">
        {impact.business_units_affected.map((unit) => (
          <span key={unit}>{unit}</span>
        ))}
      </div>
    </section>
  );
}
