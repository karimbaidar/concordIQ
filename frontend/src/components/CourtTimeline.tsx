import type { DeliberationTranscript, TranscriptMode } from "../types";

interface CourtTimelineProps {
  transcript: DeliberationTranscript;
}

const MODE_LABEL: Record<TranscriptMode, string> = {
  live_captured: "Live · model-generated narration",
  replayed: "Replay · captured Court",
  deterministic_fallback: "Deterministic narration · no model",
};

const OUTCOME_LABEL: Record<DeliberationTranscript["outcome"], string> = {
  proposal: "Governed proposal preserved — human approval required",
  refusal: "Governance refusal preserved — routed to humans",
  no_action: "Wording decoy dismissed — no proposal",
};

const ROUND_LABEL: Record<number, string> = {
  0: "Convene",
  1: "Steward positions",
  2: "Investigation plan",
  3: "Evidence review",
  4: "Targeted replan",
  5: "Cross-examination",
  6: "Steward responses",
  7: "Reflection",
  8: "Authority",
  9: "Audit ruling",
};

export function CourtTimeline({ transcript }: CourtTimelineProps) {
  const rounds = Array.from(
    transcript.turns.reduce((grouped, turn) => {
      const existing = grouped.get(turn.round_no) ?? [];
      existing.push(turn);
      grouped.set(turn.round_no, existing);
      return grouped;
    }, new Map<number, DeliberationTranscript["turns"]>()),
  );

  return (
    <section className="surface court-timeline" aria-labelledby="court-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Phase 2 · Microsoft Agent Framework</span>
          <h2 id="court-title">Semantic Court over frozen run</h2>
        </div>
        <span className={`court-mode mode-${transcript.mode}`}>
          {MODE_LABEL[transcript.mode]}
        </span>
      </div>

      <p className="court-summary">
        Source run <code>{transcript.source_run_id}</code>. The Court read the stored case,
        cited its evidence, and preserved verdict <strong>{transcript.verdict}</strong>.
      </p>

      <div className="court-workflow" aria-label="Court workflow trace">
        {transcript.workflow_trace.map((agent, index) => (
          <span key={`${agent}-${index}`}>
            {agent}
            {index < transcript.workflow_trace.length - 1 && <i aria-hidden="true">→</i>}
          </span>
        ))}
      </div>

      <ol className="court-round-groups">
        {rounds.map(([roundNo, turns]) => (
          <li key={roundNo} className="court-round-group">
            <header>
              <span>Round {roundNo}</span>
              <strong>{ROUND_LABEL[roundNo] ?? "Deliberation"}</strong>
            </header>
            <ol className="court-turns">
              {turns.map((turn) => (
                <li key={turn.turn_no} className={`court-turn role-${turn.role}`}>
                  <div className="court-turn-body">
                    <header>
                      <strong className="court-agent-name">{turn.agent_id}</strong>
                      {turn.speaking_for && (
                        <span className="court-speaking-for">for {turn.speaking_for}</span>
                      )}
                      <span className={`court-disposition disposition-${turn.disposition}`}>
                        {turn.disposition}
                      </span>
                      <span
                        className={`court-provenance ${
                          turn.provenance.generated ? "is-live" : "is-fallback"
                        }`}
                      >
                        {turn.provenance.generated ? "live narration" : "reviewed narration"}
                      </span>
                    </header>
                    <p className="court-content">{turn.content}</p>
                    {(turn.tool_calls.length > 0 || turn.cited_evidence_ids.length > 0) && (
                      <div className="court-tool-row">
                        {turn.tool_calls.map((call) => (
                          <code key={call} className="court-tool">
                            {call}
                          </code>
                        ))}
                        {turn.cited_evidence_ids.length > 0 && (
                          <span className="court-evidence">
                            {turn.cited_evidence_ids.length} stored evidence refs
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </li>
        ))}
      </ol>

      <footer className={`court-ruling outcome-${transcript.outcome}`}>
        <strong>Court audit</strong>
        <span>
          {OUTCOME_LABEL[transcript.outcome]} Authority:{" "}
          {transcript.authority_owner ?? transcript.authority_status}. Evidence set:{" "}
          {transcript.source_evidence_ids.length}/{transcript.source_evidence_ids.length} exact.
        </span>
      </footer>
    </section>
  );
}
