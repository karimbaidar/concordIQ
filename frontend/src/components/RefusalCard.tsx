import type { AuthorityAssessment } from "../types";

interface RefusalCardProps {
  reason: string;
  authority: AuthorityAssessment;
}

export function RefusalCard({ reason, authority }: RefusalCardProps) {
  return (
    <section className="decision-card refusal-card" aria-labelledby="refusal-title">
      <div className="decision-icon" aria-hidden="true">
        !
      </div>
      <div className="decision-content">
        <span className="section-kicker">Governance boundary reached</span>
        <h2 id="refusal-title">Concord IQ refuses to choose a winner</h2>
        <p>{reason}</p>
        <div className="authority-rules">
          {authority.rules.map((rule) => (
            <article key={rule.semantic_dimension}>
              <span>{rule.semantic_dimension.replaceAll("-", " ")}</span>
              <strong>{rule.status}</strong>
              <p>{rule.rationale}</p>
            </article>
          ))}
        </div>
        <footer>
          <span>Required next step</span>
          <strong>Human governance approval</strong>
        </footer>
      </div>
    </section>
  );
}
