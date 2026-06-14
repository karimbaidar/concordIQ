import type { ReconciliationCase } from "../types";

interface DecoyRuledOutProps {
  result: ReconciliationCase;
}

export function DecoyRuledOut({ result }: DecoyRuledOutProps) {
  const count = result.execution_results[0]?.entity_count ?? 0;
  const total = result.execution_results[0]?.metric_total ?? 0;
  const governed = result.governed_canonical;
  const entityLabel = result.impact_assessment?.entity_label ?? "entities";

  return (
    <section className="decision-card decoy-card" aria-labelledby="decoy-title">
      <div className="decision-icon" aria-hidden="true">
        =
      </div>
      <div className="decision-content">
        <span className="section-kicker">
          {governed ? "Governed rerun" : "False conflict rejected"}
        </span>
        <h2 id="decoy-title">
          {governed
            ? `Canonical v${governed.version} executed cleanly`
            : "Different words, same operational result"}
        </h2>
        {governed ? (
          <p>
            The approved canonical selected {count} {entityLabel} with a represented
            total of{" "}
            {new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "USD",
              maximumFractionDigits: 0,
            }).format(total)}
            . No competing unqualified definition or new proposal was introduced.
          </p>
        ) : (
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
        )}
        <div className="equality-proof">
          <span>{governed ? "Canonical population" : "Entity sets"}</span>
          <strong>{governed ? "Verified" : "Equal"}</strong>
          <span>{governed ? "New proposal" : "Result rows"}</span>
          <strong>{governed ? "None" : "Equal"}</strong>
          <span>{governed ? "Impact delta" : "Metric totals"}</span>
          <strong>{governed ? "Zero" : "Equal"}</strong>
        </div>
      </div>
    </section>
  );
}
