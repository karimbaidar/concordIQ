import type { ReconciliationCase } from "../types";

interface ReasoningTimelineProps {
  result: ReconciliationCase;
}

function checkLabel(check: string) {
  return check.replaceAll("_", " ");
}

export function ReasoningTimeline({ result }: ReasoningTimelineProps) {
  return (
    <section className="surface reasoning-timeline" aria-labelledby="timeline-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Microsoft Agent Framework</span>
          <h2 id="timeline-title">Agent trace</h2>
        </div>
        <span className="quiet-label">{result.agent_trace.length} specialist steps</span>
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
