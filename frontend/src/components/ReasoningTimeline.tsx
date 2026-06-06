import type { ReconciliationCase } from "../types";

interface ReasoningTimelineProps {
  result: ReconciliationCase;
}

function stateLabel(state: string) {
  return state
    .toLowerCase()
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

function checkLabel(check: string) {
  return check.replaceAll("_", " ");
}

export function ReasoningTimeline({ result }: ReasoningTimelineProps) {
  return (
    <section className="surface reasoning-timeline" aria-labelledby="timeline-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Blackboard execution</span>
          <h2 id="timeline-title">Reasoning timeline</h2>
        </div>
        <span className="quiet-label">{result.audit_log.length} verified states</span>
      </div>
      <ol>
        {result.audit_log.map((entry) => (
          <li key={`${entry.sequence}-${entry.state}`}>
            <span className="timeline-index">{entry.sequence.toString().padStart(2, "0")}</span>
            <span className="timeline-line" aria-hidden="true" />
            <div>
              <header>
                <strong>{stateLabel(entry.state)}</strong>
                <span>{entry.agent}</span>
              </header>
              <p>{entry.summary}</p>
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
