import { useEffect, useId, useMemo, useState } from "react";

import type {
  ImpactAssessment,
  ProposalDecisionResult,
  ReconciliationCase,
  WhatIfResult,
} from "../types";

interface MeaningGraphProps {
  result: ReconciliationCase;
  whatIf: WhatIfResult | null;
  impact: ImpactAssessment | null;
  mergedDecision?: ProposalDecisionResult | null;
}

type MeaningGraphState =
  | "diverged"
  | "exploring"
  | "refused"
  | "aligned"
  | "converged";

const NODE_X = 735;
const NODE_WIDTH = 290;
const NODE_HEIGHT = 104;
const TERM_X = 155;
const TERM_Y = 235;

function usePrefersReducedMotion() {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia?.(query).matches === true,
  );

  useEffect(() => {
    if (!window.matchMedia) {
      return;
    }
    const media = window.matchMedia(query);
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);

  return reduced;
}

function compactCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCount(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function splitTerm(term: string): [string, string | null] {
  const words = term.trim().split(/\s+/);
  if (words.length < 2) {
    return [term, null];
  }
  const midpoint = Math.ceil(words.length / 2);
  return [words.slice(0, midpoint).join(" "), words.slice(midpoint).join(" ")];
}

function nodeCenters(count: number) {
  if (count <= 1) {
    return [235];
  }
  if (count === 2) {
    return [145, 325];
  }
  return [95, 235, 375];
}

function graphState(
  result: ReconciliationCase,
  whatIf: WhatIfResult | null,
  mergedDecision: ProposalDecisionResult | null | undefined,
): MeaningGraphState {
  if (result.governed_canonical || mergedDecision?.status === "approved") {
    return "converged";
  }
  if (whatIf) {
    return "exploring";
  }
  if (result.refusal_reason) {
    return "refused";
  }
  return result.verdict === "conflict" ? "diverged" : "aligned";
}

export function MeaningGraph({
  result,
  whatIf,
  impact,
  mergedDecision = null,
}: MeaningGraphProps) {
  const accessibleId = useId();
  const reducedMotion = usePrefersReducedMotion();
  const state = graphState(result, whatIf, mergedDecision);
  const term = result.resolved_concept?.canonical_name ?? result.request.term;
  const [termLineOne, termLineTwo] = splitTerm(term);
  const evaluationByBinding = useMemo(
    () =>
      new Map(
        result.execution_results.map((evaluation) => [
          evaluation.binding_id,
          evaluation,
        ]),
      ),
    [result.execution_results],
  );
  const nodes = result.binding_semantics.slice(0, 3).map((binding) => {
    const evaluation = evaluationByBinding.get(binding.binding_id);
    const explored = whatIf?.binding_id === binding.binding_id;
    return {
      binding,
      count: explored
        ? whatIf.whatif.entity_count
        : (evaluation?.entity_count ?? 0),
      windowDays: explored
        ? whatIf.overrides.time_window_days
        : binding.time_window_days,
      explored,
    };
  });
  const centers = nodeCenters(nodes.length);
  const canonical = result.governed_canonical;
  const canonicalSourceId =
    canonical?.source_definition_id ??
    mergedDecision?.canonical_source_definition_id ??
    result.reconciliation_proposal?.canonical_source_definition_id;
  const canonicalBinding =
    result.binding_semantics.find(
      (binding) => binding.definition_id === canonicalSourceId,
    ) ?? result.binding_semantics[0];
  const canonicalEvaluation =
    result.execution_results.find(
      (evaluation) => evaluation.definition_id === canonicalSourceId,
    ) ?? result.execution_results[0];
  const canonicalVersion =
    canonical?.version ?? mergedDecision?.canonical_version ?? "pending";
  const approvedBy =
    canonical?.approved_by ?? mergedDecision?.decided_by ?? "configured owner";
  const domainViewCount =
    canonical?.domain_views.length ?? result.binding_semantics.length;
  const impactCount = impact?.customer_count_delta ?? 0;
  const impactValue = impact?.arr_delta ?? 0;
  const entityLabel = impact?.entity_label ?? "entities";
  const singularEntityLabel = entityLabel === "learners" ? "learner" : "entity";
  const valueLabel = impact?.value_label ?? "metric delta";
  const valueSummary = valueLabel === "metric delta" ? "" : ` ${valueLabel}`;
  const statusLabel = {
    diverged: "Conflict proven by SQL",
    exploring: "Exploration - not governed",
    refused: "Conflict proven - merge refused",
    aligned: "Operationally equivalent",
    converged: `Converged - Canonical v${canonicalVersion}`,
  }[state];
  const nodeSummary = nodes
    .map(
      ({ binding, count, windowDays, explored }) =>
        `${binding.owner} selects ${formatCount(count)} ${entityLabel}${
          windowDays ? ` with a ${windowDays}-day ${explored ? "what-if" : "window"}` : ""
        }`,
    )
    .join("; ");
  const summary =
    state === "converged"
      ? `${term} is governed by Canonical v${canonicalVersion}, approved by ${approvedBy}. ${domainViewCount} named domain views are retained for audit and domain use.`
      : state === "refused"
        ? `${term} remains forked: ${nodeSummary}. Concord IQ refused an automatic merge because no single authority can approve it.`
        : state === "aligned"
          ? `${term} has ${nodes.length} definitions that execute to equivalent populations. No operational conflict was found.`
          : `${term} is ${state === "exploring" ? "being explored ephemerally" : "operationally forked"}: ${nodeSummary}. The current spread is ${formatCount(impactCount)} ${entityLabel} and ${compactCurrency(impactValue)}${valueSummary}.`;

  return (
    <section
      className={`meaning-graph meaning-graph-${state}${
        reducedMotion ? " is-reduced-motion" : ""
      }`}
      aria-labelledby={`${accessibleId}-heading`}
      data-state={state}
      data-reduced-motion={reducedMotion ? "true" : "false"}
    >
      <header className="meaning-graph-heading">
        <div>
          <span className="section-kicker">Meaning fork</span>
          <h2 id={`${accessibleId}-heading`}>
            One governed term.{" "}
            {state === "converged"
              ? "One governed meaning."
              : "Different operational truths."}
          </h2>
        </div>
        <span className="meaning-graph-status" data-testid="meaning-graph-status">
          {statusLabel}
        </span>
      </header>

      <div className="meaning-graph-canvas">
        <svg
          viewBox="0 0 1080 470"
          role="img"
          tabIndex={0}
          aria-labelledby={`${accessibleId}-title ${accessibleId}-description`}
        >
          <title id={`${accessibleId}-title`}>Meaning graph for {term}</title>
          <desc id={`${accessibleId}-description`}>{summary}</desc>

          <g aria-hidden="true">
            <circle className="meaning-term-halo" cx={TERM_X} cy={TERM_Y} r="93" />
            <circle className="meaning-term-node" cx={TERM_X} cy={TERM_Y} r="72" />
            <text className="meaning-term-label" x={TERM_X} y={termLineTwo ? 226 : 238}>
              <tspan x={TERM_X}>{termLineOne}</tspan>
              {termLineTwo && (
                <tspan x={TERM_X} dy="25">
                  {termLineTwo}
                </tspan>
              )}
            </text>
            <text className="meaning-term-kicker" x={TERM_X} y="174">
              BUSINESS TERM
            </text>

            {state === "converged" ? (
              <>
                <path
                  className="meaning-edge meaning-edge-converged"
                  d={`M ${TERM_X + 72} ${TERM_Y} C 385 ${TERM_Y}, 510 ${TERM_Y}, 650 ${TERM_Y}`}
                />
                <circle className="meaning-edge-pulse" cx="450" cy={TERM_Y} r="7" />
                <g className="meaning-canonical-node" transform="translate(650 130)">
                  <rect width="340" height="210" rx="24" />
                  <text className="meaning-node-kicker" x="28" y="35">
                    GOVERNED CANONICAL
                  </text>
                  <text className="meaning-canonical-title" x="28" y="73">
                    Canonical v{canonicalVersion}
                  </text>
                  <text className="meaning-canonical-count" x="28" y="126">
                    {formatCount(canonicalEvaluation?.entity_count ?? 0)}
                  </text>
                  <text className="meaning-node-unit" x="150" y="126">
                    {entityLabel}
                  </text>
                  <text className="meaning-node-meta" x="28" y="158">
                    {canonicalBinding?.time_window_days
                      ? `${canonicalBinding.time_window_days}-day governed window`
                      : "Selected reporting period"}
                  </text>
                  <text className="meaning-node-meta" x="28" y="184">
                    Approved by {approvedBy}
                  </text>
                </g>
                <g className="meaning-domain-history" transform="translate(700 377)">
                  <circle cx="0" cy="0" r="5" />
                  <circle cx="18" cy="0" r="5" />
                  <circle cx="36" cy="0" r="5" />
                  <text x="54" y="4">
                    {domainViewCount} named domain views retained
                  </text>
                </g>
              </>
            ) : (
              <>
                {nodes.map((node, index) => {
                  const centerY = centers[index];
                  return (
                    <g key={node.binding.binding_id}>
                      <path
                        className={`meaning-edge meaning-edge-${state}${
                          node.explored ? " is-explored" : ""
                        }`}
                        d={`M ${TERM_X + 72} ${TERM_Y} C 390 ${TERM_Y}, 505 ${centerY}, ${NODE_X} ${centerY}`}
                      />
                      <circle
                        className={`meaning-edge-pulse${node.explored ? " is-explored" : ""}`}
                        cx="500"
                        cy={(TERM_Y + centerY) / 2}
                        r="6"
                      />
                      <g
                        className={`meaning-definition-node${
                          node.explored ? " is-explored" : ""
                        }`}
                        transform={`translate(${NODE_X} ${centerY - NODE_HEIGHT / 2})`}
                        data-owner={node.binding.owner}
                        data-count={node.count}
                        data-window-days={node.windowDays ?? ""}
                      >
                        <rect width={NODE_WIDTH} height={NODE_HEIGHT} rx="18" />
                        <text className="meaning-node-owner" x="20" y="27">
                          {node.binding.owner}
                        </text>
                        <text className="meaning-node-count" x="20" y="69">
                          {formatCount(node.count)}
                        </text>
                        <text className="meaning-node-unit" x="112" y="69">
                          {entityLabel}
                        </text>
                        <text className="meaning-node-meta" x="20" y="91">
                          {node.windowDays
                            ? `${node.windowDays}-day ${node.explored ? "what-if" : "window"}`
                            : "Selected reporting period"}
                        </text>
                      </g>
                    </g>
                  );
                })}
                <g
                  className="meaning-impact-badge"
                  transform="translate(360 174)"
                  data-testid="meaning-graph-impact"
                >
                  <rect width="240" height="116" rx="20" />
                  <text className="meaning-impact-kicker" x="22" y="30">
                    {state === "aligned" ? "EXECUTED RESULT" : "PROVEN IMPACT"}
                  </text>
                  <text className="meaning-impact-count" x="22" y="69">
                    {formatCount(impactCount)}
                  </text>
                  <text className="meaning-impact-unit" x="94" y="69">
                    {singularEntityLabel} spread
                  </text>
                  <text className="meaning-impact-money" x="22" y="96">
                    {compactCurrency(impactValue)}
                  </text>
                </g>
                {state === "refused" && (
                  <g className="meaning-refusal-marker" transform="translate(367 316)">
                    <rect width="226" height="48" rx="13" />
                    <text x="113" y="20">
                      NO AUTHORIZED MERGE
                    </text>
                    <text x="113" y="36">
                      Human governance required
                    </text>
                  </g>
                )}
              </>
            )}
          </g>
        </svg>
      </div>

      <div className="meaning-graph-footer">
        <p data-testid="meaning-graph-summary" aria-live="polite">
          <strong>Text equivalent:</strong> {summary}
        </p>
        <span>Rendered from executed results. The LLM does not determine this graph.</span>
      </div>
    </section>
  );
}
