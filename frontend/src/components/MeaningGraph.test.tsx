import { cleanup, render, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  DefinitionBinding,
  ImpactAssessment,
  ProposalDecisionResult,
  ReconciliationCase,
  WhatIfResult,
} from "../types";
import { MeaningGraph } from "./MeaningGraph";

const owners = ["Finance", "Sales", "Customer Success"];
const counts = [1600, 1500, 1334];
const windows = [90, 180, 30];

function makeBinding(owner: string, index: number): DefinitionBinding {
  return {
    binding_id: `binding-${index}`,
    definition_id: `definition-${index}`,
    concept_id: "active-customer",
    name: `${owner} Active Customer`,
    owner,
    rule_text: `${owner} operational rule.`,
    semantic_dimensions: ["time-window"],
    source_tables: ["customers"],
    entity_key: "customer_id",
    grain: "customer",
    population: `${owner} population.`,
    time_window_days: windows[index],
    filters: [],
    exclusions: [],
    sql_template: "SELECT customer_id FROM customers",
  };
}

function makeCase(): ReconciliationCase {
  const bindings = owners.map(makeBinding);
  return {
    run_id: "run-1",
    request: {
      question: "Why do our Active Customer dashboards disagree?",
      term: "Active Customer",
      period: { start_date: "2026-03-04", end_date: "2026-06-01" },
    },
    state: "COMPLETE",
    context_packet: {
      provider_metadata: {
        name: "LocalProvider",
        mode: "local",
        uses_cloud: false,
        data_type: "synthetic",
      },
      active_scenario: "active_customer",
    },
    resolved_concept: {
      concept_id: "active-customer",
      canonical_name: "Active Customer",
      description: "Synthetic governed concept.",
      aliases: [],
      definition_ids: bindings.map((binding) => binding.definition_id),
    },
    binding_semantics: bindings,
    conflict_hypotheses: [],
    execution_results: bindings.map((binding, index) => ({
      binding_id: binding.binding_id,
      definition_id: binding.definition_id,
      concept_id: binding.concept_id,
      period: { start_date: "2026-03-04", end_date: "2026-06-01" },
      entity_ids: [],
      rows: [],
      entity_count: counts[index],
      metric_total: 200_000_000 - index * 16_599_000,
      executed_sql: "SELECT customer_id FROM customers",
    })),
    verdict: "conflict",
    verification_status: "passed",
    verifier_attempts: 1,
    verification_recovery: null,
    impact_assessment: {
      rank: 1,
      severity: "high",
      customer_count_delta: 266,
      arr_delta: 33_198_000,
      reports_affected: 3,
      business_units_affected: owners,
      decision_criticality: "high",
    },
    authority_assessment: {
      status: "clear",
      owner: "Data Governance Council",
      rules: [],
      rationale: "Configured owner.",
    },
    governed_canonical: null,
    reconciliation_proposal: {
      canonical_definition: "Contract plus qualifying usage.",
      rationale: "The executed populations differ.",
      migration_notes: [],
      expected_dashboard_impact: "$33.2M",
      authority_owner: "Data Governance Council",
      requires_human_approval: true,
      evidence_refs: [],
      canonical_source_definition_id: "definition-2",
    },
    refusal_reason: null,
    requires_human_approval: true,
    verifier_report: null,
    narrations: [],
    evidence: [],
    agent_trace: [],
    audit_log: [],
  };
}

function renderGraph(
  result: ReconciliationCase,
  options: {
    whatIf?: WhatIfResult | null;
    impact?: ImpactAssessment | null;
    decision?: ProposalDecisionResult | null;
  } = {},
) {
  return render(
    <MeaningGraph
      result={result}
      whatIf={options.whatIf ?? null}
      impact={options.impact ?? result.impact_assessment}
      mergedDecision={options.decision ?? null}
    />,
  );
}

function graphSnapshot(container: HTMLElement) {
  const graph = container.querySelector<HTMLElement>(".meaning-graph");
  const nodeElements = Array.from(
    container.querySelectorAll<SVGGElement>(".meaning-definition-node"),
  );
  return {
    state: graph?.dataset.state,
    reducedMotion: graph?.dataset.reducedMotion,
    status: within(graph!).getByTestId("meaning-graph-status").textContent,
    impact: within(graph!).queryByTestId("meaning-graph-impact")?.textContent,
    nodes: nodeElements.map((node) => ({
      owner: node.dataset.owner,
      count: node.dataset.count,
      windowDays: node.dataset.windowDays,
      explored: node.classList.contains("is-explored"),
    })),
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("MeaningGraph", () => {
  it("renders a deterministic diverged fork with exact counts, windows, and impact", () => {
    const { container } = renderGraph(makeCase());

    expect(graphSnapshot(container)).toMatchInlineSnapshot(`
      {
        "impact": "PROVEN IMPACT266entity spread$33.2M",
        "nodes": [
          {
            "count": "1600",
            "explored": false,
            "owner": "Finance",
            "windowDays": "90",
          },
          {
            "count": "1500",
            "explored": false,
            "owner": "Sales",
            "windowDays": "180",
          },
          {
            "count": "1334",
            "explored": false,
            "owner": "Customer Success",
            "windowDays": "30",
          },
        ],
        "reducedMotion": "false",
        "state": "diverged",
        "status": "Conflict proven by SQL",
      }
    `);
    expect(
      within(container).getByRole("img", {
        name: /^Meaning graph for Active Customer/,
      }),
    ).toHaveAttribute("tabindex", "0");
    expect(within(container).getByTestId("meaning-graph-summary")).toHaveTextContent(
      "The current spread is 266 entities and $33.2M.",
    );
  });

  it("animates real what-if values but disables motion for reduced-motion users", () => {
    vi.stubGlobal("matchMedia", () => ({
      matches: true,
      media: "(prefers-reduced-motion: reduce)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    const whatIf: WhatIfResult = {
      term: "Active Customer",
      binding_id: "binding-0",
      overrides: { time_window_days: 120 },
      baseline: { entity_count: 1600, metric_value: 200_000_000 },
      whatif: { entity_count: 1667, metric_value: 208_567_000 },
      delta: { entity_count: 67, metric_value: 8_567_000 },
      sql: "SELECT customer_id FROM customers",
      ephemeral: true,
      note: "Exploration only.",
    };
    const impact = {
      ...makeCase().impact_assessment!,
      customer_count_delta: 333,
      arr_delta: 41_765_000,
    };
    const { container } = renderGraph(makeCase(), { whatIf, impact });

    expect(graphSnapshot(container)).toMatchInlineSnapshot(`
      {
        "impact": "PROVEN IMPACT333entity spread$41.77M",
        "nodes": [
          {
            "count": "1667",
            "explored": true,
            "owner": "Finance",
            "windowDays": "120",
          },
          {
            "count": "1500",
            "explored": false,
            "owner": "Sales",
            "windowDays": "180",
          },
          {
            "count": "1334",
            "explored": false,
            "owner": "Customer Success",
            "windowDays": "30",
          },
        ],
        "reducedMotion": "true",
        "state": "exploring",
        "status": "Exploration - not governed",
      }
    `);
    expect(container.querySelector(".meaning-graph")).toHaveClass("is-reduced-motion");
  });

  it("keeps an authority refusal visibly forked", () => {
    const refused = makeCase();
    refused.refusal_reason = "Authority is ambiguous.";
    refused.authority_assessment = {
      status: "ambiguous",
      owner: null,
      rules: [],
      rationale: "No single owner.",
    };
    refused.reconciliation_proposal = null;
    const { container } = renderGraph(refused);

    expect(graphSnapshot(container)).toMatchInlineSnapshot(`
      {
        "impact": "PROVEN IMPACT266entity spread$33.2M",
        "nodes": [
          {
            "count": "1600",
            "explored": false,
            "owner": "Finance",
            "windowDays": "90",
          },
          {
            "count": "1500",
            "explored": false,
            "owner": "Sales",
            "windowDays": "180",
          },
          {
            "count": "1334",
            "explored": false,
            "owner": "Customer Success",
            "windowDays": "30",
          },
        ],
        "reducedMotion": "false",
        "state": "refused",
        "status": "Conflict proven - merge refused",
      }
    `);
    expect(container).toHaveTextContent("Human governance required");
  });

  it("collapses an approved fork into one governed canonical node", () => {
    const governed = makeCase();
    const domainViews = governed.binding_semantics;
    governed.binding_semantics = [
      {
        ...domainViews[2],
        name: "Canonical v1",
        owner: "Data Governance Council",
      },
    ];
    governed.execution_results = [governed.execution_results[2]];
    governed.verdict = "consistent";
    governed.impact_assessment = {
      ...governed.impact_assessment!,
      rank: 0,
      severity: "low",
      customer_count_delta: 0,
      arr_delta: 0,
      decision_criticality: "low",
    };
    governed.governed_canonical = {
      canonical_definition_id: "canonical-1",
      version: "1",
      rule_text: "Contract plus qualifying usage.",
      source_definition_id: "definition-2",
      approved_by: "Data Governance Council",
      approved_at: "2026-06-09T18:30:00Z",
      approving_run_id: "run-1",
      registry_scope: "concord_iq",
      domain_views: domainViews,
    };
    governed.reconciliation_proposal = null;
    governed.requires_human_approval = false;
    const { container } = renderGraph(governed);

    expect(graphSnapshot(container)).toMatchInlineSnapshot(`
      {
        "impact": undefined,
        "nodes": [],
        "reducedMotion": "false",
        "state": "converged",
        "status": "Converged - Canonical v1",
      }
    `);
    expect(container).toHaveTextContent("Canonical v1");
    expect(container).toHaveTextContent("1,334");
    expect(container).toHaveTextContent("3 named domain views retained");
    expect(within(container).getByTestId("meaning-graph-summary")).toHaveTextContent(
      "approved by Data Governance Council",
    );
  });
});
