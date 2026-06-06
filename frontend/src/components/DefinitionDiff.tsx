import type { ReconciliationCase } from "../types";

interface DefinitionDiffProps {
  result: ReconciliationCase;
}

function humanize(value: string) {
  return value.replaceAll("-", " ");
}

export function DefinitionDiff({ result }: DefinitionDiffProps) {
  const evaluations = new Map(
    result.execution_results.map((evaluation) => [evaluation.binding_id, evaluation]),
  );

  return (
    <section className="surface definition-diff" aria-labelledby="definition-diff-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Operational semantics</span>
          <h2 id="definition-diff-title">Why the definitions differ</h2>
        </div>
        <span className="quiet-label">{result.binding_semantics.length} definitions</span>
      </div>
      <div className="definition-grid">
        {result.binding_semantics.map((binding) => {
          const evaluation = evaluations.get(binding.binding_id);
          return (
            <article className="definition-card" key={binding.binding_id}>
              <header>
                <span>{binding.owner}</span>
                <strong>{binding.name}</strong>
              </header>
              <p>{binding.rule_text}</p>
              <dl>
                <div>
                  <dt>Population</dt>
                  <dd>{binding.population}</dd>
                </div>
                <div>
                  <dt>Window</dt>
                  <dd>
                    {binding.time_window_days
                      ? `${binding.time_window_days} trailing days`
                      : "Selected reporting period"}
                  </dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{binding.source_tables.join(" + ")}</dd>
                </div>
              </dl>
              <div className="dimension-list">
                {binding.semantic_dimensions.map((dimension) => (
                  <span key={dimension}>{humanize(dimension)}</span>
                ))}
              </div>
              <footer>
                <strong>{evaluation?.entity_count ?? 0}</strong>
                <span>entities after execution</span>
              </footer>
            </article>
          );
        })}
      </div>
    </section>
  );
}
