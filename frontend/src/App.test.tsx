import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { ReconciliationCase } from "./types";

const scenarios = [
  {
    scenario_id: "active-customer",
    term: "Active Customer",
    question: "Why do our Active Customer dashboards disagree?",
  },
  {
    scenario_id: "net-revenue",
    term: "Net Revenue",
    question: "Are our Net Revenue definitions operationally equivalent?",
  },
  {
    scenario_id: "churned-customer",
    term: "Churned Customer",
    question: "Can we choose one enterprise Churned Customer definition?",
  },
];

function makeCase(
  scenario: "active_customer" | "net_revenue" | "churned_customer",
): ReconciliationCase {
  const owners =
    scenario === "active_customer"
      ? ["Finance", "Sales", "Customer Success"]
      : scenario === "net_revenue"
        ? ["Finance", "Sales"]
        : ["Finance", "Customer Success"];
  const counts =
    scenario === "active_customer" ? [96, 90, 80] : scenario === "net_revenue" ? [96, 96] : [20, 40];
  const verdict = scenario === "net_revenue" ? "consistent" : "conflict";
  const bindings = owners.map((owner, index) => ({
    binding_id: `${scenario}-${index}`,
    definition_id: `${scenario}-definition-${index}`,
    concept_id: scenario,
    name: `${owner} definition`,
    owner,
    rule_text: `${owner} operational rule.`,
    semantic_dimensions: ["reporting-period"],
    source_tables: ["customers"],
    entity_key: "customer_id",
    grain: "customer",
    population: `${owner} customer population.`,
    time_window_days: index ? 30 : 90,
    filters: ["synthetic = true"],
    exclusions: [],
    sql_template: "SELECT 1",
  }));
  const evidence = bindings.map((binding, index) => ({
    evidence_id: `00000000-0000-0000-0000-00000000000${index}`,
    binding_id: binding.binding_id,
    definition_id: binding.definition_id,
    source_ref: `duckdb:${binding.binding_id}`,
    entity_count: counts[index],
    metric_total: scenario === "net_revenue" ? 1000000 : 1000000 - index * 100000,
    entity_ids: Array.from({ length: counts[index] }, (_, entityIndex) => `C-${entityIndex}`),
    sql_text: "SELECT customer_id FROM customers ORDER BY customer_id",
  }));
  const refusalReason =
    scenario === "churned_customer"
      ? "Automatic reconciliation refused because authority is ambiguous. Human approval is required."
      : null;

  return {
    run_id: "00000000-0000-0000-0000-000000000099",
    request: {
      question: "Test question",
      term: scenario.replaceAll("_", " "),
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
      active_scenario: scenario,
    },
    resolved_concept: {
      concept_id: scenario,
      canonical_name: scenario.replaceAll("_", " "),
      description: "Synthetic governed concept.",
      aliases: [],
      definition_ids: bindings.map((binding) => binding.definition_id),
    },
    binding_semantics: bindings,
    execution_results: bindings.map((binding, index) => ({
      binding_id: binding.binding_id,
      definition_id: binding.definition_id,
      concept_id: scenario,
      period: { start_date: "2026-03-04", end_date: "2026-06-01" },
      entity_ids: evidence[index].entity_ids,
      rows: evidence[index].entity_ids.map((entityId) => ({
        entity_id: entityId,
        metric_value: 100,
      })),
      entity_count: counts[index],
      metric_total: evidence[index].metric_total,
      executed_sql: evidence[index].sql_text,
    })),
    verdict,
    verification_status: "passed",
    verifier_attempts: 1,
    verification_recovery: null,
    impact_assessment: {
      rank: verdict === "consistent" ? 0 : 1,
      severity: verdict === "consistent" ? "low" : "high",
      customer_count_delta: Math.max(...counts) - Math.min(...counts),
      arr_delta: verdict === "consistent" ? 0 : 200000,
      reports_affected: owners.length,
      business_units_affected: owners,
      decision_criticality: verdict === "consistent" ? "low" : "high",
    },
    authority_assessment: {
      status: scenario === "churned_customer" ? "ambiguous" : "clear",
      owner: scenario === "churned_customer" ? null : "Data Governance Council",
      rules: [
        {
          concept_id: scenario,
          semantic_dimension: "reporting-period",
          status: scenario === "churned_customer" ? "ambiguous" : "clear",
          owner: scenario === "churned_customer" ? null : "Data Governance Council",
          rationale: "Configured synthetic authority rule.",
        },
      ],
      rationale:
        scenario === "churned_customer"
          ? "No single owner can approve the definition."
          : "Configured authority can approve the definition.",
    },
    reconciliation_proposal:
      scenario === "active_customer"
        ? {
            canonical_definition: "Active Customer requires contract and qualifying usage.",
            rationale: "The executed definitions diverge materially.",
            migration_notes: ["Rename domain views.", "Request steward approval."],
            expected_dashboard_impact: "Up to 16 customers differ.",
            authority_owner: "Data Governance Council",
            requires_human_approval: true,
            evidence_refs: evidence.map((item) => item.evidence_id),
          }
        : null,
    refusal_reason: refusalReason,
    requires_human_approval: scenario !== "net_revenue",
    verifier_report: {
      passed: true,
      checks: {
        every_result_has_sql_evidence: true,
        scenario_outcome_is_supported: true,
      },
      failures: [],
      attempt: 1,
      recoverable: false,
      recovery_stage: null,
      advisory_notes: ["All deterministic blocking checks passed."],
      narration: null,
    },
    narrations: [
      {
        task: "decision",
        text: "The executed definitions materially diverge.",
        provider_name: "DisabledLLMProvider",
        model: null,
        generated: false,
        fallback_reason: "LLM narration is disabled.",
      },
      {
        task: "verifier",
        text: "All deterministic blocking checks passed.",
        provider_name: "DisabledLLMProvider",
        model: null,
        generated: false,
        fallback_reason: "LLM narration is disabled.",
      },
      {
        task: "audit",
        text: "Concord IQ completed the verified case.",
        provider_name: "DisabledLLMProvider",
        model: null,
        generated: false,
        fallback_reason: "LLM narration is disabled.",
      },
    ],
    evidence,
    agent_trace: [
      {
        step_number: 1,
        agent_name: "CoordinatorAgent",
        input_summary: "Requested a governed reconciliation.",
        output_summary: "Created the typed casefile and workflow plan.",
        evidence_ids: [],
        provider_mode: "local",
        verifier_status: null,
        duration_ms: 0.1,
      },
      {
        step_number: 2,
        agent_name: "DataExecutionAgent",
        input_summary: `Execute ${bindings.length} trusted bindings.`,
        output_summary: `Settled verdict as ${verdict}.`,
        evidence_ids: evidence.map((item) => item.evidence_id),
        provider_mode: "local",
        verifier_status: null,
        duration_ms: 2.4,
      },
      {
        step_number: 3,
        agent_name: "SkepticalVerifierAgent",
        input_summary: `Verify ${evidence.length} evidence records.`,
        output_summary: "Passed deterministic checks.",
        evidence_ids: evidence.map((item) => item.evidence_id),
        provider_mode: "local",
        verifier_status: "passed",
        duration_ms: 0.4,
      },
    ],
    audit_log: [
      {
        sequence: 1,
        state: "RESOLVE_CONCEPT",
        agent: "ConceptResolverAgent",
        summary: "Resolved the governed concept.",
        status: "completed",
      },
      {
        sequence: 2,
        state: "VERIFY",
        agent: "SkepticalVerifierAgent",
        summary: "All deterministic blocking checks passed.",
        status: "completed",
      },
    ],
  };
}

function mockJson(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

describe("Concord IQ demo", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const url = String(input);
        if (url.endsWith("/health")) {
          return mockJson({
            status: "ok",
            provider: "LocalProvider",
            cloud_enabled: false,
            data_type: "synthetic",
            llm_provider: "DisabledLLMProvider",
            llm_enabled: false,
            llm_model: null,
          });
        }
        if (url.endsWith("/demo/scenarios")) {
          return mockJson(scenarios);
        }
        if (url.endsWith("/demo/run/active-customer")) {
          return mockJson(makeCase("active_customer"));
        }
        if (url.endsWith("/demo/run/net-revenue")) {
          return mockJson(makeCase("net_revenue"));
        }
        return mockJson(makeCase("churned_customer"));
      }),
    );
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows provider safety and an evidence-backed semantic proposal", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Cloud disabled")).toBeInTheDocument();
    expect(screen.getByText("synthetic data")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));

    expect(await screen.findByText("Material conflict confirmed")).toBeInTheDocument();
    expect(screen.getByText("Proposed canonical definition")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent trace" })).toBeInTheDocument();
    expect(screen.getByText("DataExecutionAgent")).toBeInTheDocument();
    expect(screen.getAllByText("3 evidence refs")).toHaveLength(2);
    expect(screen.getByText("Skeptical verifier passed")).toBeInTheDocument();
    expect(screen.getByLabelText("3 evidence records")).toBeInTheDocument();
    expect(screen.getByText("Evidence narration")).toBeInTheDocument();
    expect(screen.getAllByText("deterministic fallback")).toHaveLength(3);
  });

  it("surfaces both the decoy and governed-refusal outcomes", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => expect(screen.getByText("Net Revenue")).toBeInTheDocument());
    // Scope to the scenario picker so the NL chat suggestions don't disambiguate.
    const scenarioList = screen.getByRole("list");
    await user.click(within(scenarioList).getByRole("button", { name: /net revenue/i }));
    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));

    expect(
      await screen.findByText("Different words, same operational result"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("2 evidence records")).toBeInTheDocument();

    await user.click(within(scenarioList).getByRole("button", { name: /churned customer/i }));
    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));

    expect(
      await screen.findByText("Concord IQ refuses to choose a winner"),
    ).toBeInTheDocument();
    expect(screen.getByText("Human governance approval")).toBeInTheDocument();
  });
});
