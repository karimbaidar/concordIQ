import { useMemo, useState } from "react";

import type { DemoScenario } from "../types";

interface TermSearchProps {
  scenarios: DemoScenario[];
  selectedId: string;
  busy: boolean;
  hostedRuntime?: boolean;
  onSelect: (scenarioId: string) => void;
  onRun: () => void;
  onInvestigate?: (term: string) => void;
}

const SCENARIO_LABELS: Record<string, string> = {
  "active-customer": "Material conflict",
  "net-revenue": "Wording decoy",
  "churned-customer": "Governed refusal",
};

export function TermSearch({
  scenarios,
  selectedId,
  busy,
  hostedRuntime = false,
  onSelect,
  onRun,
  onInvestigate,
}: TermSearchProps) {
  const [query, setQuery] = useState("");
  const trimmedQuery = query.trim();
  const visibleScenarios = useMemo(() => {
    const normalized = trimmedQuery.toLowerCase();
    if (!normalized) {
      return scenarios;
    }
    return scenarios.filter((scenario) =>
      `${scenario.term} ${scenario.question}`.toLowerCase().includes(normalized),
    );
  }, [trimmedQuery, scenarios]);
  const selected = scenarios.find((scenario) => scenario.scenario_id === selectedId);
  const canInvestigateTerm =
    Boolean(onInvestigate) && trimmedQuery.length > 0 && visibleScenarios.length === 0;

  return (
    <section className="term-search" aria-labelledby="term-search-title">
      <div className="section-kicker">Reconciliation workbench</div>
      <h2 id="term-search-title">Which meaning should we test?</h2>
      <label className="search-field">
        <span className="sr-only">Search governed terms</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
        </svg>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search governed terms"
        />
      </label>
      <div className="scenario-list" role="list">
        {visibleScenarios.map((scenario) => (
          <div className="scenario-listitem" role="listitem" key={scenario.scenario_id}>
            <button
              className={`scenario-option ${
                selectedId === scenario.scenario_id ? "is-selected" : ""
              }`}
              aria-pressed={selectedId === scenario.scenario_id}
              onClick={() => onSelect(scenario.scenario_id)}
              type="button"
            >
              <span className="scenario-radio" aria-hidden="true" />
              <span>
                <strong>{scenario.term}</strong>
                <small>{SCENARIO_LABELS[scenario.scenario_id]}</small>
              </span>
            </button>
          </div>
        ))}
      </div>
      {canInvestigateTerm && (
        <div className="term-investigate" role="note">
          <p>No governed scenario matches “{trimmedQuery}”.</p>
          <button
            type="button"
            className="ghost-button"
            disabled={busy}
            onClick={() => onInvestigate?.(trimmedQuery)}
          >
            Investigate “{trimmedQuery}” as a term
          </button>
        </div>
      )}
      <button
        className="run-button"
        disabled={!selected || busy}
        onClick={onRun}
        type="button"
      >
        <span>{busy ? "Running deterministic checks" : "Analyze disagreement"}</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>
      <p className="run-note">
        {hostedRuntime
          ? "Calls the deployed Agent Framework runtime; deterministic tools still own the verdict."
          : "Executes trusted SQL locally. No LLM or cloud call participates in the verdict."}
      </p>
    </section>
  );
}
