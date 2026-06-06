import type { ReconciliationCase } from "../types";

interface DecoyRuledOutProps {
  result: ReconciliationCase;
}

export function DecoyRuledOut({ result }: DecoyRuledOutProps) {
  const count = result.execution_results[0]?.entity_count ?? 0;
  const total = result.execution_results[0]?.metric_total ?? 0;

  return (
    <section className="decision-card decoy-card" aria-labelledby="decoy-title">
      <div className="decision-icon" aria-hidden="true">
        =
      </div>
      <div className="decision-content">
        <span className="section-kicker">False conflict rejected</span>
        <h2 id="decoy-title">Different words, same operational result</h2>
        <p>
          Both definitions selected the same {count} entities with the same total of{" "}
          {new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            maximumFractionDigits: 0,
          }).format(total)}
          . Concord IQ rules the disagreement consistent without proposing a semantic
          change.
        </p>
        <div className="equality-proof">
          <span>Entity sets</span>
          <strong>Equal</strong>
          <span>Result rows</span>
          <strong>Equal</strong>
          <span>Metric totals</span>
          <strong>Equal</strong>
        </div>
      </div>
    </section>
  );
}
