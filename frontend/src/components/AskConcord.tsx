import { type FormEvent, useState } from "react";

import { askConcord } from "../api";
import type { QueryResult, ReconciliationCase } from "../types";

interface AskConcordProps {
  onAnswer: (caseResult: ReconciliationCase) => void;
  busy: boolean;
  setBusy: (busy: boolean) => void;
  scenarioPack?: "learning" | "business";
}

const BUSINESS_SUGGESTIONS = [
  "Why do our active customer numbers disagree?",
  "Are our net revenue definitions equivalent?",
  "Do Sales and Marketing agree on a qualified lead?",
];

const LEARNING_SUGGESTIONS = [
  "Who is Certification Ready?",
  "Why do our certification readiness counts disagree?",
  "Which readiness definition is governed?",
];

export function AskConcord({
  onAnswer,
  busy,
  setBusy,
  scenarioPack = "business",
}: AskConcordProps) {
  const [question, setQuestion] = useState("");
  const [grounded, setGrounded] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const suggestions =
    scenarioPack === "learning" ? LEARNING_SUGGESTIONS : BUSINESS_SUGGESTIONS;
  const placeholder =
    scenarioPack === "learning"
      ? "Why do our certification readiness counts disagree?"
      : "Why do our active customer numbers disagree?";

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
      <span className="section-kicker">
        {scenarioPack === "learning" ? "Ask in operational terms" : "Ask in business terms"}
      </span>
      <h2 id="ask-title">Ask Concord IQ</h2>
      <p>Ask a question; Concord IQ grounds it in the ontology, then reconciles it on data.</p>
      <form className="ask-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          placeholder={placeholder}
          aria-label={
            scenarioPack === "learning" ? "Operational question" : "Business question"
          }
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="submit" className="primary-button" disabled={busy}>
          Ask Concord IQ
        </button>
      </form>
      <div className="ask-suggestions">
        {suggestions.map((suggestion) => (
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
