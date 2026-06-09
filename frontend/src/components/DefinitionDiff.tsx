import { useEffect, useMemo, useState } from "react";

import type { ReconciliationCase, WhatIfResult } from "../types";

interface DefinitionDiffProps {
  result: ReconciliationCase;
  whatIf: WhatIfResult | null;
  whatIfBusy: boolean;
  whatIfError: string | null;
  whatIfEnabled: boolean;
  onWhatIf: (bindingId: string, timeWindowDays: number) => void;
  onResetWhatIf: () => void;
}

function humanize(value: string) {
  return value.replaceAll("-", " ");
}

function formatSigned(value: number) {
  return new Intl.NumberFormat("en-US", {
    signDisplay: "always",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatSignedCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    signDisplay: "always",
    maximumFractionDigits: 0,
  }).format(value);
}

export function DefinitionDiff({
  result,
  whatIf,
  whatIfBusy,
  whatIfError,
  whatIfEnabled,
  onWhatIf,
  onResetWhatIf,
}: DefinitionDiffProps) {
  const evaluations = new Map(
    result.execution_results.map((evaluation) => [evaluation.binding_id, evaluation]),
  );
  const editableBindings = useMemo(
    () => result.binding_semantics.filter((binding) => binding.time_window_days !== null),
    [result.binding_semantics],
  );
  const [selectedBindingId, setSelectedBindingId] = useState(
    editableBindings[0]?.binding_id ?? "",
  );
  const selectedBinding =
    editableBindings.find((binding) => binding.binding_id === selectedBindingId) ??
    editableBindings[0];
  const governedDays = selectedBinding?.time_window_days ?? 30;
  const [timeWindowDays, setTimeWindowDays] = useState(governedDays);

  useEffect(() => {
    const firstBinding = editableBindings[0];
    setSelectedBindingId(firstBinding?.binding_id ?? "");
    setTimeWindowDays(firstBinding?.time_window_days ?? 30);
  }, [editableBindings, result.run_id]);

  useEffect(() => {
    if (
      !whatIfEnabled ||
      !selectedBinding ||
      timeWindowDays === selectedBinding.time_window_days
    ) {
      return;
    }
    const timeout = window.setTimeout(() => {
      onWhatIf(selectedBinding.binding_id, timeWindowDays);
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [onWhatIf, selectedBinding, timeWindowDays, whatIfEnabled]);

  function selectBinding(bindingId: string) {
    const binding = editableBindings.find((item) => item.binding_id === bindingId);
    setSelectedBindingId(bindingId);
    setTimeWindowDays(binding?.time_window_days ?? 30);
    onResetWhatIf();
  }

  function resetToGoverned() {
    setTimeWindowDays(governedDays);
    onResetWhatIf();
  }

  return (
    <section className="surface definition-diff" aria-labelledby="definition-diff-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Operational semantics</span>
          <h2 id="definition-diff-title">Why the definitions differ</h2>
        </div>
        <span className="quiet-label">{result.binding_semantics.length} definitions</span>
      </div>
      <div className="definition-grid">
        {result.binding_semantics.map((binding) => {
          const evaluation = evaluations.get(binding.binding_id);
          const explored =
            whatIf?.binding_id === binding.binding_id ? whatIf.whatif : null;
          return (
            <article
              className={`definition-card${explored ? " is-exploring" : ""}`}
              key={binding.binding_id}
            >
              <header>
                <span>{binding.owner}</span>
                <strong>{binding.name}</strong>
              </header>
              <p>{binding.rule_text}</p>
              <dl>
                <div>
                  <dt>Population</dt>
                  <dd>{binding.population}</dd>
                </div>
                <div>
                  <dt>Window</dt>
                  <dd>
                    {binding.time_window_days
                      ? `${binding.time_window_days} trailing days`
                      : "Selected reporting period"}
                  </dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{binding.source_tables.join(" + ")}</dd>
                </div>
              </dl>
              <div className="dimension-list">
                {binding.semantic_dimensions.map((dimension) => (
                  <span key={dimension}>{humanize(dimension)}</span>
                ))}
              </div>
              <footer>
                <strong
                  className="rederived-value"
                  key={explored?.entity_count ?? evaluation?.entity_count ?? 0}
                >
                  {explored?.entity_count ?? evaluation?.entity_count ?? 0}
                </strong>
                <span>entities after execution</span>
              </footer>
            </article>
          );
        })}
      </div>
      {whatIfEnabled && selectedBinding && (
        <div className="whatif-lab">
          <div className="whatif-heading">
            <div>
              <span className="section-kicker">Live deterministic sandbox</span>
              <h3>Edit one definition and re-run its SQL</h3>
            </div>
            {whatIf && <span className="exploration-chip">Exploration — not governed</span>}
          </div>
          <div className="whatif-controls">
            <label>
              Definition
              <select
                value={selectedBinding.binding_id}
                onChange={(event) => selectBinding(event.target.value)}
              >
                {editableBindings.map((binding) => (
                  <option key={binding.binding_id} value={binding.binding_id}>
                    {binding.owner}: {binding.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="window-control">
              <span>
                Time window
                <strong>{timeWindowDays} days</strong>
              </span>
              <div className="window-stepper">
                <button
                  type="button"
                  aria-label={`Decrease time window for ${selectedBinding.name}`}
                  disabled={timeWindowDays <= 30}
                  onClick={() => setTimeWindowDays((current) => Math.max(30, current - 30))}
                >
                  −
                </button>
                <input
                  aria-label={`Time window for ${selectedBinding.name}`}
                  type="range"
                  min="30"
                  max="180"
                  step="1"
                  value={timeWindowDays}
                  onChange={(event) => setTimeWindowDays(Number(event.target.value))}
                />
                <button
                  type="button"
                  aria-label={`Increase time window for ${selectedBinding.name}`}
                  disabled={timeWindowDays >= 180}
                  onClick={() =>
                    setTimeWindowDays((current) => Math.min(180, current + 30))
                  }
                >
                  +
                </button>
              </div>
              <small>Governed value: {governedDays} days</small>
            </label>
            <button
              className="ghost-button"
              type="button"
              onClick={resetToGoverned}
              disabled={!whatIf && timeWindowDays === governedDays}
            >
              Reset to governed
            </button>
          </div>
          <div className="whatif-proof" aria-live="polite">
            {whatIfBusy && <span>Re-executing trusted SQL…</span>}
            {!whatIfBusy && whatIf && (
              <>
                <span>
                  Governed <strong>{whatIf.baseline.entity_count}</strong>
                </span>
                <span>
                  What-if{" "}
                  <strong className="rederived-value" key={whatIf.whatif.entity_count}>
                    {whatIf.whatif.entity_count}
                  </strong>
                </span>
                <span>
                  <strong>{formatSigned(whatIf.delta.entity_count)}</strong> entities
                </span>
                <span>
                  <strong>{formatSignedCurrency(whatIf.delta.metric_value)}</strong> metric
                </span>
              </>
            )}
            {!whatIfBusy && !whatIf && (
              <span>Move the window to re-derive this population from synthetic data.</span>
            )}
          </div>
          {whatIfError && (
            <p className="whatif-error" role="alert">
              {whatIfError}
            </p>
          )}
          <p className="whatif-note">
            {whatIf?.note ??
              "Exploration only — not governed, not persisted, no proposal, no audit."}
          </p>
        </div>
      )}
    </section>
  );
}
