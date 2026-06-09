import { useState } from "react";

import { decideProposal } from "../api";
import type { ProposalDecisionResult, ReconciliationProposal } from "../types";

interface SemanticPullRequestProps {
  proposal: ReconciliationProposal;
  runId: string;
  onRerun: () => Promise<void>;
}

function formatDecisionTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function SemanticPullRequest({
  proposal,
  runId,
  onRerun,
}: SemanticPullRequestProps) {
  const [decision, setDecision] = useState<ProposalDecisionResult | null>(null);
  const [pending, setPending] = useState(false);
  const [rerunPending, setRerunPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(action: "approve" | "reject") {
    setPending(true);
    setError(null);
    try {
      // Only the configured authority owner may decide; the gate is enforced server-side.
      const result = await decideProposal(runId, action, proposal.authority_owner);
      setDecision(result);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "The approval gate rejected this.",
      );
    } finally {
      setPending(false);
    }
  }

  async function rerunGovernedDefinition() {
    setRerunPending(true);
    setError(null);
    try {
      await onRerun();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The governed re-run could not be completed.",
      );
      setRerunPending(false);
    }
  }

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
        <span className={`draft-badge status-${decision?.status ?? "draft"}`}>
          {decision?.status === "approved"
            ? `Merged · Canonical v${decision.canonical_version}`
            : decision
              ? `${decision.status} · ${decision.decided_by}`
              : "Draft · approval required"}
        </span>
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
      <div className="pr-gate">
        <p>
          Only <strong>{proposal.authority_owner}</strong> can merge this change. Concord IQ
          enforces the owner server-side and records the decision in the audit trail.
        </p>
        {decision?.status === "approved" ? (
          <div className="merged-state" aria-live="polite">
            <div>
              <span className="merged-check" aria-hidden="true">
                ✓
              </span>
              <div>
                <strong>Merged — canonical definition is now governed</strong>
                <p>
                  Canonical v{decision.canonical_version} · approved by{" "}
                  {decision.decided_by} · {formatDecisionTime(decision.decided_at)}
                </p>
              </div>
            </div>
            <span className="registry-scope">
              Concord IQ registry · no Fabric/Foundry writeback
            </span>
            <button
              type="button"
              className="primary-button"
              disabled={rerunPending}
              onClick={rerunGovernedDefinition}
            >
              {rerunPending ? "Re-running governed definition…" : "Re-run with governed definition"}
            </button>
          </div>
        ) : decision ? (
          <span className={`gate-result gate-${decision.status}`}>
            Changes requested by {decision.decided_by}
          </span>
        ) : (
          <div className="pr-actions">
            <button
              type="button"
              className="primary-button"
              disabled={pending}
              onClick={() => decide("approve")}
            >
              Approve &amp; merge
            </button>
            <button
              type="button"
              className="ghost-button"
              disabled={pending}
              onClick={() => decide("reject")}
            >
              Request changes
            </button>
          </div>
        )}
        {error && (
          <span className="gate-result gate-error" role="alert">
            {error}
          </span>
        )}
      </div>
    </section>
  );
}
