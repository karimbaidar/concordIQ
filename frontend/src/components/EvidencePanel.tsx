import type { ReconciliationCase } from "../types";

interface EvidencePanelProps {
  result: ReconciliationCase;
}

export function EvidencePanel({ result }: EvidencePanelProps) {
  const bindings = new Map(
    result.binding_semantics.map((binding) => [binding.binding_id, binding]),
  );

  return (
    <section className="surface evidence-panel" aria-labelledby="evidence-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Stored proof</span>
          <h2 id="evidence-title">Evidence and executed SQL</h2>
        </div>
        <span className="quiet-label">{result.evidence.length} records</span>
      </div>
      <div className="evidence-list">
        {result.evidence.map((evidence, index) => {
          const binding = bindings.get(evidence.binding_id);
          return (
            <details key={evidence.evidence_id} open={index === 0}>
              <summary>
                <span className="evidence-number">{index + 1}</span>
                <span>
                  <strong>{binding?.name ?? evidence.definition_id}</strong>
                  <small>{evidence.source_ref}</small>
                </span>
                <span className="evidence-count">{evidence.entity_count} entities</span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m7 10 5 5 5-5" />
                </svg>
              </summary>
              <div className="evidence-body">
                <div className="sql-header">
                  <span>Executed SQL</span>
                  <code>{evidence.binding_id}</code>
                </div>
                <pre>
                  <code>{evidence.sql_text}</code>
                </pre>
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
