import type { ReconciliationProposal } from "../types";

interface SemanticPullRequestProps {
  proposal: ReconciliationProposal;
}

export function SemanticPullRequest({ proposal }: SemanticPullRequestProps) {
  return (
    <section className="semantic-pr" aria-labelledby="semantic-pr-title">
      <header>
        <div className="pr-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div>
          <span className="section-kicker">Semantic pull request</span>
          <h2 id="semantic-pr-title">Proposed canonical definition</h2>
        </div>
        <span className="draft-badge">Draft · approval required</span>
      </header>
      <div className="pr-definition">
        <span>Canonical definition</span>
        <blockquote>{proposal.canonical_definition}</blockquote>
      </div>
      <div className="pr-grid">
        <div>
          <span>Why this change</span>
          <p>{proposal.rationale}</p>
        </div>
        <div>
          <span>Expected dashboard impact</span>
          <p>{proposal.expected_dashboard_impact}</p>
        </div>
      </div>
      <div className="migration-checklist">
        <span>Migration checklist</span>
        {proposal.migration_notes.map((note) => (
          <p key={note}>
            <i aria-hidden="true">✓</i>
            {note}
          </p>
        ))}
      </div>
      <footer>
        <span>Authority owner</span>
        <strong>{proposal.authority_owner}</strong>
        <span>Evidence references</span>
        <strong>{proposal.evidence_refs.length}</strong>
      </footer>
    </section>
  );
}
