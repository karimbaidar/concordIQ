import type { NarrationResult } from "../types";

interface NarrationPanelProps {
  narrations: NarrationResult[];
}

function taskLabel(task: NarrationResult["task"]) {
  const labels = {
    decision: "Decision explanation",
    verifier: "Verifier advisory",
    audit: "Audit summary",
  };
  return labels[task];
}

export function NarrationPanel({ narrations }: NarrationPanelProps) {
  if (!narrations.length) {
    return null;
  }

  return (
    <section className="surface narration-panel" aria-labelledby="narration-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Optional language layer</span>
          <h2 id="narration-title">Evidence narration</h2>
        </div>
        <span className="quiet-label">Never changes the verdict</span>
      </div>
      <div className="narration-grid">
        {narrations.map((narration) => (
          <article key={narration.task}>
            <header>
              <strong>{taskLabel(narration.task)}</strong>
              <span className={narration.generated ? "is-generated" : "is-fallback"}>
                {narration.generated ? narration.model : "deterministic fallback"}
              </span>
            </header>
            <p>{narration.text}</p>
            <small>{narration.provider_name}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
