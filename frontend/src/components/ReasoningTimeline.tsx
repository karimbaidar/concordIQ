import type { ConflictHypothesis, ReconciliationCase } from "../types";

interface ReasoningTimelineProps {
  result: ReconciliationCase;
}

function checkLabel(check: string) {
  return check.replaceAll("_", " ");
}

function bindingOwner(result: ReconciliationCase, bindingId: string) {
  return (
    result.binding_semantics.find((binding) => binding.binding_id === bindingId)?.owner ??
    bindingId
  );
}

function dataRuling(result: ReconciliationCase, hypothesis: ConflictHypothesis) {
  const evaluations = new Map(
    result.execution_results.map((evaluation) => [evaluation.binding_id, evaluation]),
  );
  const leftCount = evaluations.get(hypothesis.left_binding_id)?.entity_count ?? 0;
  const rightCount = evaluations.get(hypothesis.right_binding_id)?.entity_count ?? 0;
  if (hypothesis.data_verdict === "confirmed") {
    return `Confirmed: executed entity sets differ (${leftCount} vs ${rightCount}).`;
  }
  if (hypothesis.data_verdict === "overturned") {
    return `Overturned: executed entity sets are equal (${leftCount} = ${rightCount}).`;
  }
  return "Pending deterministic execution.";
}

export function ReasoningTimeline({ result }: ReasoningTimelineProps) {
  const evidence = new Map(result.evidence.map((item) => [item.evidence_id, item]));

  return (
    <section className="surface reasoning-timeline" aria-labelledby="timeline-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Phase 1 · Microsoft Agent Framework</span>
          <h2 id="timeline-title">Evidence workflow complete</h2>
        </div>
        <span className="quiet-label">
          {result.agent_trace.length} Agent Framework stages
        </span>
      </div>
      <ol>
        {result.agent_trace.map((step) => (
          <li key={`${step.step_number}-${step.agent_name}`}>
            <span className="timeline-index">
              {step.step_number.toString().padStart(2, "0")}
            </span>
            <span className="timeline-line" aria-hidden="true" />
            <div className="trace-step">
              <header>
                <strong>{step.agent_name}</strong>
                <span className="trace-meta">
                  <span>{step.provider_mode}</span>
                  {step.evidence_ids.length > 0 && (
                    <span>{step.evidence_ids.length} evidence refs</span>
                  )}
                  {step.verifier_status && <span>{step.verifier_status}</span>}
                  {step.duration_ms !== null && <span>{step.duration_ms.toFixed(1)} ms</span>}
                </span>
              </header>
              <p className="trace-input">
                <span>Input</span>
                {step.input_summary}
              </p>
              <p className="trace-output">
                <span>Output</span>
                {step.output_summary}
              </p>
              {step.deliberations.length > 0 && (
                <div className="deliberation-panel">
                  <div className="deliberation-labels">
                    <span>Deterministic</span>
                    <span>LLM did not decide</span>
                  </div>
                  {step.deliberations.map((hypothesis) => {
                    const citedEvidence = hypothesis.evidence_ids
                      .map((evidenceId) => evidence.get(evidenceId))
                      .filter((item) => item !== undefined);
                    return (
                      <article
                        className={`deliberation-card ruling-${hypothesis.data_verdict}`}
                        key={`${hypothesis.left_binding_id}-${hypothesis.right_binding_id}`}
                      >
                        <header>
                          <strong>
                            {bindingOwner(result, hypothesis.left_binding_id)} ↔{" "}
                            {bindingOwner(result, hypothesis.right_binding_id)}
                          </strong>
                          <span>{hypothesis.data_verdict}</span>
                        </header>
                        <dl>
                          <div>
                            <dt>Claim</dt>
                            <dd>{hypothesis.claim}</dd>
                          </div>
                          <div>
                            <dt>Challenge</dt>
                            <dd>{hypothesis.skeptic_challenge}</dd>
                          </div>
                          <div>
                            <dt>Data ruling</dt>
                            <dd>{dataRuling(result, hypothesis)}</dd>
                          </div>
                        </dl>
                        <details>
                          <summary>
                            {citedEvidence.length} evidence records · exact SQL
                          </summary>
                          <div className="deliberation-evidence">
                            {citedEvidence.map((item) => (
                              <div key={item.evidence_id}>
                                <span>
                                  {bindingOwner(result, item.binding_id)} ·{" "}
                                  {item.entity_count} entities
                                </span>
                                <code>{item.sql_text}</code>
                              </div>
                            ))}
                          </div>
                        </details>
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
      {result.verifier_report && (
        <div
          className={`verifier-panel ${
            result.verifier_report.passed ? "is-passed" : "is-failed"
          }`}
        >
          <header>
            <span className="verifier-icon" aria-hidden="true">
              {result.verifier_report.passed ? "✓" : "!"}
            </span>
            <div>
              <strong>
                Skeptical verifier {result.verifier_report.passed ? "passed" : "failed"}
              </strong>
              <span>Deterministic blocking checks</span>
            </div>
          </header>
          <ul>
            {Object.entries(result.verifier_report.checks).map(([check, passed]) => (
              <li key={check}>
                <span>{passed ? "✓" : "×"}</span>
                {checkLabel(check)}
              </li>
            ))}
          </ul>
          <p className="verifier-advisory">
            {result.verifier_report.advisory_notes[0]}
          </p>
        </div>
      )}
    </section>
  );
}
