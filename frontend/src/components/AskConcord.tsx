import { type FormEvent, useState } from "react";

import { askConcord } from "../api";
import type { QueryResult, ReconciliationCase } from "../types";

interface AskConcordProps {
  onAnswer: (caseResult: ReconciliationCase) => void;
  busy: boolean;
  setBusy: (busy: boolean) => void;
}

const SUGGESTIONS = [
  "Why do our active customer numbers disagree?",
  "Are our net revenue definitions equivalent?",
  "Do Sales and Marketing agree on a qualified lead?",
];

export function AskConcord({ onAnswer, busy, setBusy }: AskConcordProps) {
  const [question, setQuestion] = useState("");
  const [grounded, setGrounded] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(value: string) {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await askConcord(trimmed);
      setGrounded(response.query);
      if (response.case) {
        onAnswer(response.case);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "The grounded query failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(question);
  }

  return (
    <section className="ask-concord surface" aria-labelledby="ask-title">
      <span className="section-kicker">Ask in business terms</span>
      <h2 id="ask-title">Ask Concord IQ</h2>
      <p>Ask a question; Concord IQ grounds it in the ontology, then reconciles it on data.</p>
      <form className="ask-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          placeholder="Why do our active customer numbers disagree?"
          aria-label="Business question"
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="submit" className="primary-button" disabled={busy}>
          Ask Concord IQ
        </button>
      </form>
      <div className="ask-suggestions">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className="ghost-button"
            disabled={busy}
            onClick={() => {
              setQuestion(suggestion);
              void submit(suggestion);
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
      {grounded && (
        <div className={`ask-answer ${grounded.matched ? "matched" : "unmatched"}`}>
          <p>{grounded.answer}</p>
          {grounded.matched && (
            <span className="ask-grounding">
              Grounded by {grounded.grounding_provider} · {grounded.citations.length} definitions
              cited
            </span>
          )}
        </div>
      )}
      {error && (
        <span className="gate-result gate-error" role="alert">
          {error}
        </span>
      )}
    </section>
  );
}
