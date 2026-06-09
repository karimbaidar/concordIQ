import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { ConflictHypothesis, ReconciliationCase } from "./types";

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
  const hypotheses: ConflictHypothesis[] = bindings.flatMap((left, leftIndex) =>
    bindings.slice(leftIndex + 1).map((right, rightOffset) => {
      const rightIndex = leftIndex + rightOffset + 1;
      return {
        left_binding_id: left.binding_id,
        right_binding_id: right.binding_id,
        differing_dimensions: ["reporting-period"],
        rationale: `${left.owner} and ${right.owner} use different operational wording.`,
        claim: `${left.owner} and ${right.owner} are suspected to select different populations.`,
        skeptic_challenge:
          "Operational wording alone is not proof. Require unequal executed entity sets.",
        data_verdict: scenario === "net_revenue" ? "overturned" : "confirmed",
        evidence_ids: [evidence[leftIndex].evidence_id, evidence[rightIndex].evidence_id],
      };
    }),
  );
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
    conflict_hypotheses: hypotheses,
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
    governed_canonical: null,
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
            canonical_source_definition_id:
              "active_customer-definition-2",
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
        deliberations: [],
        provider_mode: "local",
        verifier_status: null,
        duration_ms: 0.1,
      },
      {
        step_number: 2,
        agent_name: "ConflictHypothesisAgent",
        input_summary: `Compare ${bindings.length} normalized bindings.`,
        output_summary: "Recorded deterministic data rulings.",
        evidence_ids: [],
        deliberations: hypotheses,
        provider_mode: "local",
        verifier_status: null,
        duration_ms: 0.3,
      },
      {
        step_number: 3,
        agent_name: "DataExecutionAgent",
        input_summary: `Execute ${bindings.length} trusted bindings.`,
        output_summary: `Settled verdict as ${verdict}.`,
        evidence_ids: evidence.map((item) => item.evidence_id),
        deliberations: [],
        provider_mode: "local",
        verifier_status: null,
        duration_ms: 2.4,
      },
      {
        step_number: 4,
        agent_name: "SkepticalVerifierAgent",
        input_summary: `Verify ${evidence.length} evidence records.`,
        output_summary: "Passed deterministic checks.",
        evidence_ids: evidence.map((item) => item.evidence_id),
        deliberations: [],
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

function makeGovernedCase(): ReconciliationCase {
  const governed = makeCase("active_customer");
  const domainViews = governed.binding_semantics;
  const source = domainViews[2];
  const sourceResult = governed.execution_results[2];
  const sourceEvidence = governed.evidence[2];
  return {
    ...governed,
    run_id: "00000000-0000-0000-0000-000000000100",
    binding_semantics: [
      {
        ...source,
        name: "Canonical v1 — approved by Data Governance Council",
        owner: "Data Governance Council",
        rule_text: "Active Customer requires contract and qualifying usage.",
      },
    ],
    conflict_hypotheses: [],
    execution_results: [sourceResult],
    evidence: [sourceEvidence],
    verdict: "consistent",
    impact_assessment: {
      ...governed.impact_assessment!,
      rank: 0,
      severity: "low",
      customer_count_delta: 0,
      arr_delta: 0,
      decision_criticality: "low",
    },
    governed_canonical: {
      canonical_definition_id: "00000000-0000-0000-0000-000000000200",
      version: "1",
      rule_text: "Active Customer requires contract and qualifying usage.",
      source_definition_id: source.definition_id,
      approved_by: "Data Governance Council",
      approved_at: "2026-06-09T18:30:00Z",
      approving_run_id: governed.run_id,
      registry_scope: "concord_iq",
      domain_views: domainViews,
    },
    reconciliation_proposal: null,
    requires_human_approval: false,
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
        if (url.endsWith("/reconcile/whatif")) {
          return mockJson({
            term: "active customer",
            binding_id: "active_customer-0",
            overrides: { time_window_days: 120 },
            baseline: { entity_count: 96, metric_value: 1000000 },
            whatif: { entity_count: 102, metric_value: 1050000 },
            delta: { entity_count: 6, metric_value: 50000 },
            sql: "SELECT 1 -- trailing 120 days",
            ephemeral: true,
            note: "Exploration only — not governed, not persisted, no proposal, no audit.",
          });
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
    expect(screen.getByText("LLM did not decide")).toBeInTheDocument();
    expect(screen.getAllByText("Data ruling")).toHaveLength(3);
    expect(
      screen.getByText("Confirmed: executed entity sets differ (96 vs 90)."),
    ).toBeInTheDocument();
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
    expect(screen.getByText("Operationally equivalent")).toBeInTheDocument();
    expect(
      screen
        .getByRole("img", { name: /Meaning graph for net revenue/i })
        .closest("section"),
    ).toHaveAttribute("data-state", "aligned");
    expect(screen.getByLabelText("2 evidence records")).toBeInTheDocument();
    expect(
      screen.getByText("Overturned: executed entity sets are equal (96 = 96)."),
    ).toBeInTheDocument();
    expect(screen.getByText("LLM did not decide")).toBeInTheDocument();

    await user.click(within(scenarioList).getByRole("button", { name: /churned customer/i }));
    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));

    expect(
      await screen.findByText("Concord IQ refuses to choose a winner"),
    ).toBeInTheDocument();
    expect(screen.getByText("Conflict proven - merge refused")).toBeInTheDocument();
    expect(
      screen
        .getByRole("img", { name: /Meaning graph for churned customer/i })
        .closest("section"),
    ).toHaveAttribute("data-state", "refused");
    expect(screen.getByText("Human governance approval")).toBeInTheDocument();
  });

  it("labels Foundry Agent Service as the hosted cloud runtime", async () => {
    const hostedCase = makeCase("active_customer");
    if (hostedCase.context_packet) {
      hostedCase.context_packet.provider_metadata = {
        name: "Foundry Agent Service",
        mode: "foundry_hosted",
        uses_cloud: true,
        data_type: "hosted runtime",
      };
    }
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const url = String(input);
        if (url.endsWith("/health")) {
          return mockJson({
            status: "ok",
            workflow_mode: "strict",
            provider: "Foundry Agent Service",
            provider_mode: "foundry_hosted",
            runtime: "Foundry Agent Service",
            cloud_enabled: true,
            data_type: "hosted runtime",
            llm_provider: "DisabledLLMProvider",
            llm_enabled: false,
            llm_model: null,
          });
        }
        if (url.endsWith("/demo/scenarios")) {
          return mockJson(scenarios);
        }
        return mockJson(hostedCase);
      }),
    );
    const user = userEvent.setup();

    render(<App />);

    expect(
      await screen.findByText("Runtime: Foundry Agent Service"),
    ).toBeInTheDocument();
    expect(screen.getByText("hosted runtime")).toBeInTheDocument();
    expect(screen.getByText("Cloud enabled")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Calls the deployed Agent Framework runtime; deterministic tools still own the verdict.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Foundry Agent Service runtime · replay-grounded proof · cloud enabled",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));
    expect(await screen.findByText("Material conflict confirmed")).toBeInTheDocument();
    expect(screen.getByText("foundry_hosted")).toBeInTheDocument();
  });

  it("re-derives one local definition and resets to governed values", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /analyze disagreement/i }),
    );
    expect(await screen.findByText("Material conflict confirmed")).toBeInTheDocument();

    const slider = screen.getByRole("slider", {
      name: "Time window for Finance definition",
    });
    expect(slider).toHaveValue("90");
    fireEvent.change(slider, { target: { value: "120" } });

    expect(await screen.findByText("Exploration — not governed")).toBeInTheDocument();
    expect(screen.getByText("+6")).toBeInTheDocument();
    expect(screen.getByText("+$50,000")).toBeInTheDocument();
    expect(
      within(document.querySelector(".impact-panel") as HTMLElement).getByText("22"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/reconcile/whatif",
        expect.objectContaining({ method: "POST" }),
      ),
    );

    await user.click(screen.getByRole("button", { name: "Reset to governed" }));
    expect(slider).toHaveValue("90");
    expect(screen.queryByText("Exploration — not governed")).not.toBeInTheDocument();
    expect(
      within(document.querySelector(".impact-panel") as HTMLElement).getByText("16"),
    ).toBeInTheDocument();
  });

  it("merges a Semantic-PR and re-runs the governed canonical definition", async () => {
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
        if (url.endsWith("/approve")) {
          return mockJson({
            run_id: "00000000-0000-0000-0000-000000000099",
            term: "Active Customer",
            status: "approved",
            authority_owner: "Data Governance Council",
            decided_by: "Data Governance Council",
            decided_at: "2026-06-09T18:30:00Z",
            canonical_definition_id: "00000000-0000-0000-0000-000000000200",
            canonical_version: "1",
            canonical_source_definition_id: "active_customer-definition-2",
            registry_scope: "concord_iq",
          });
        }
        if (url.endsWith("/analyze")) {
          return mockJson(makeGovernedCase());
        }
        return mockJson(makeCase("active_customer"));
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /analyze disagreement/i }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Approve & merge" }),
    );

    expect(
      await screen.findByText("Merged — canonical definition is now governed"),
    ).toBeInTheDocument();
    expect(
      screen
        .getByRole("img", { name: /Meaning graph for active customer/i })
        .closest("section"),
    ).toHaveAttribute("data-state", "converged");
    expect(
      screen.getByText(/Canonical v1 · approved by Data Governance Council/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Concord IQ registry · no Fabric/Foundry writeback"),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Re-run with governed definition" }),
    );

    expect(
      await screen.findByText("Governed canonical v1 in force"),
    ).toBeInTheDocument();
    expect(screen.getByText("Governed: Canonical v1")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Governed meaning and named domain views" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Named departmental views")).toBeInTheDocument();
    expect(screen.getAllByText(/domain view/i).length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText("Proposed canonical definition")).not.toBeInTheDocument();
  });

  it("refuses an ungoverned term gracefully without fabricating a definition", async () => {
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
        if (url.endsWith("/analyze")) {
          return mockJson({
            refused: true,
            term: "Gross Margin",
            reason:
              "No governed definition for 'Gross Margin'. Concord IQ will not guess. " +
              "Add it to the ontology to reconcile it.",
            known_terms: [
              "Active Customer",
              "Net Revenue",
              "Churned Customer",
              "Qualified Lead",
            ],
          });
        }
        return mockJson(makeCase("active_customer"));
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    const search = await screen.findByPlaceholderText("Search governed terms");
    await user.type(search, "Gross Margin");
    await user.click(
      await screen.findByRole("button", { name: /investigate .* as a term/i }),
    );

    expect(
      await screen.findByRole("heading", { name: /Concord IQ will not guess/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No governed definition for 'Gross Margin'/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Terms Concord IQ can reconcile today:"),
    ).toBeInTheDocument();
    // Never fabricates a result for an ungoverned term.
    expect(screen.queryByText("Material conflict confirmed")).not.toBeInTheDocument();
  });
});
