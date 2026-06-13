import type { DeliberationTranscript, TranscriptMode } from "../types";

interface CourtTimelineProps {
  transcript: DeliberationTranscript;
}

const MODE_LABEL: Record<TranscriptMode, string> = {
  live_captured: "Live · model-generated",
  replayed: "Replay · captured debate",
  deterministic_fallback: "Deterministic · no model",
};

const OUTCOME_LABEL: Record<DeliberationTranscript["outcome"], string> = {
  proposal: "Governed proposal — human approval required",
  refusal: "Refused — routed to a human, minority report recorded",
  no_action: "Decoy dismissed — no reconciliation published",
};

const ROLE_LABEL: Record<string, string> = {
  orchestrator: "Orchestrator",
  steward: "Steward",
  investigator: "Investigator",
  skeptic: "Skeptic",
  authority: "Authority",
};

export function CourtTimeline({ transcript }: CourtTimelineProps) {
  return (
    <section className="surface court-timeline" aria-labelledby="court-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Multi-agent reasoning</span>
          <h2 id="court-title">The Semantic Court</h2>
        </div>
        <span className={`court-mode mode-${transcript.mode}`}>
          {MODE_LABEL[transcript.mode]}
        </span>
      </div>

      <p className="court-summary">
        The agents argue; the evidence rules. Verdict{" "}
        <strong>{transcript.verdict}</strong> · {transcript.turns.length} turns over{" "}
        {transcript.rounds} rounds.
      </p>

      <ol className="court-turns">
        {transcript.turns.map((turn) => (
          <li key={turn.turn_no} className={`court-turn role-${turn.role}`}>
            <span className="court-round" aria-hidden="true">
              R{turn.round_no}
            </span>
            <div className="court-turn-body">
              <header>
                <span className="court-role-chip">{ROLE_LABEL[turn.role] ?? turn.role}</span>
                {turn.speaking_for && (
                  <span className="court-speaking-for">for {turn.speaking_for}</span>
                )}
                <span
                  className={`court-provenance ${
                    turn.provenance.generated ? "is-live" : "is-fallback"
                  }`}
                >
                  {turn.provenance.generated ? "live" : "reviewed"}
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
                      {turn.cited_evidence_ids.length} evidence refs
                    </span>
                  )}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>

      <footer className={`court-ruling outcome-${transcript.outcome}`}>
        <strong>Ruling</strong>
        <span>{OUTCOME_LABEL[transcript.outcome]}</span>
      </footer>

      {/* [Screenshot placeholder: the Semantic Court debate timeline] */}
    </section>
  );
}
