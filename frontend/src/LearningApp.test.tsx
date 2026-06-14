import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { DeliberationTranscript, ReconciliationCase } from "./types";

const scenario = {
  scenario_id: "certification-ready",
  term: "Certification Ready",
  question:
    "Do HR, Learning and Development, and managers agree on who is Certification Ready?",
};

const owners = ["HR", "Learning & Development", "Managers"];
const counts = [80, 56, 56];
const definitionIds = [
  "certification_ready_hr",
  "certification_ready_learning",
  "certification_ready_manager",
];
const bindingIds = definitionIds.map((definitionId) => `${definitionId}_v1`);
const entityIds = [
  Array.from({ length: 80 }, (_, index) => `L${String(index + 1).padStart(3, "0")}`),
  Array.from({ length: 56 }, (_, index) => `L${String(index + 1).padStart(3, "0")}`),
  Array.from({ length: 56 }, (_, index) => `L${String(index + 41).padStart(3, "0")}`),
];
const evidenceIds = [
  "10000000-0000-0000-0000-000000000001",
  "10000000-0000-0000-0000-000000000002",
  "10000000-0000-0000-0000-000000000003",
];
const falseReadyIds = Array.from(
  { length: 24 },
  (_, index) => `L${String(index + 57).padStart(3, "0")}`,
);

const learningCase: ReconciliationCase = {
  run_id: "10000000-0000-0000-0000-000000000099",
  request: {
    question: scenario.question,
    term: scenario.term,
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
    active_scenario: "certification_ready",
  },
  resolved_concept: {
    concept_id: "certification_ready",
    canonical_name: "Certification Ready",
    description: "A learner represented as ready for an enterprise certification exam.",
    aliases: ["certification readiness"],
    definition_ids: definitionIds,
  },
  binding_semantics: owners.map((owner, index) => ({
    binding_id: bindingIds[index],
    definition_id: definitionIds[index],
    concept_id: "certification_ready",
    name: `${owner} Certification Ready`,
    owner,
    rule_text:
      index === 0
        ? "All required modules complete."
        : index === 1
          ? "All required modules complete and latest practice score at least 80 percent."
          : "All required labs complete and manager approval recorded.",
    semantic_dimensions: ["readiness-evidence"],
    source_tables: ["learners"],
    entity_key: "learner_id",
    grain: "learner",
    population: `${owner} readiness population.`,
    time_window_days: null,
    filters: ["synthetic = true"],
    exclusions: [],
    sql_template: "SELECT learner_id FROM learners",
  })),
  conflict_hypotheses: [
    [0, 1],
    [0, 2],
    [1, 2],
  ].map(([left, right]) => ({
    left_binding_id: bindingIds[left],
    right_binding_id: bindingIds[right],
    differing_dimensions: ["readiness-evidence"],
    rationale: "The owners use different operational readiness evidence.",
    claim: `${owners[left]} and ${owners[right]} may select different learners.`,
    skeptic_challenge:
      "Wording is not proof. Require unequal learner sets from executed SQL.",
    data_verdict: "confirmed",
    evidence_ids: [evidenceIds[left], evidenceIds[right]],
  })),
  execution_results: owners.map((_, index) => ({
    binding_id: bindingIds[index],
    definition_id: definitionIds[index],
    concept_id: "certification_ready",
    period: { start_date: "2026-03-04", end_date: "2026-06-01" },
    entity_ids: entityIds[index],
    rows: entityIds[index].map((entityId) => ({
      entity_id: entityId,
      metric_value: 450,
    })),
    entity_count: counts[index],
    metric_total: counts[index] * 450,
    executed_sql: "SELECT learner_id, 450 FROM learners ORDER BY learner_id",
  })),
  verdict: "conflict",
  verification_status: "passed",
  verifier_attempts: 1,
  verification_recovery: null,
  impact_assessment: {
    rank: 1,
    severity: "high",
    customer_count_delta: 24,
    arr_delta: 10_800,
    reports_affected: 3,
    business_units_affected: owners,
    decision_criticality: "high",
    entity_label: "learners",
    value_label: "exam spend at risk",
    affected_entity_ids: entityIds[0],
    false_positive_count: 24,
    false_positive_label: "false-ready learners",
    false_positive_entity_ids: falseReadyIds,
  },
  authority_assessment: {
    status: "clear",
    owner: "Learning Governance Council",
    rules: [
      {
        concept_id: "certification_ready",
        semantic_dimension: "canonical-certification-ready",
        status: "clear",
        owner: "Learning Governance Council",
        rationale: "The council owns enterprise readiness.",
      },
    ],
    rationale: "The Learning Governance Council owns enterprise readiness.",
  },
  governed_canonical: null,
  reconciliation_proposal: {
    canonical_definition:
      "Certification Ready requires all modules and a latest practice score of at least 80 percent.",
    rationale:
      "HR marks 24 learners ready who do not meet the verified practice threshold.",
    migration_notes: [
      "Keep HR and manager measures as named views.",
      "Release vouchers only after approval.",
    ],
    expected_dashboard_impact:
      "24 false-ready learners and 10,800.00 in synthetic exam spend are exposed.",
    authority_owner: "Learning Governance Council",
    requires_human_approval: true,
    evidence_refs: evidenceIds,
    canonical_source_definition_id: "certification_ready_learning",
  },
  refusal_reason: null,
  requires_human_approval: true,
  verifier_report: {
    passed: true,
    checks: {
      three_definitions_executed: true,
      false_ready_population_is_derived: true,
      exam_spend_risk_is_quantified: true,
    },
    failures: [],
    attempt: 1,
    recoverable: false,
    recovery_stage: null,
    advisory_notes: ["All deterministic checks passed."],
    narration: null,
  },
  narrations: [],
  evidence: owners.map((_, index) => ({
    evidence_id: evidenceIds[index],
    binding_id: bindingIds[index],
    definition_id: definitionIds[index],
    source_ref: `duckdb:${bindingIds[index]}`,
    entity_count: counts[index],
    metric_total: counts[index] * 450,
    entity_ids: entityIds[index],
    sql_text: "SELECT learner_id, 450 FROM learners ORDER BY learner_id",
  })),
  agent_trace: [
    {
      step_number: 1,
      agent_name: "CoordinatorAgent",
      input_summary: "Requested Certification Ready.",
      output_summary: "Created the typed workflow.",
      evidence_ids: [],
      deliberations: [],
      provider_mode: "local",
      verifier_status: null,
      duration_ms: 0.1,
    },
    {
      step_number: 2,
      agent_name: "DataExecutionAgent",
      input_summary: "Execute three trusted readiness bindings.",
      output_summary: "Settled verdict as conflict with counts 80/56/56.",
      evidence_ids: evidenceIds,
      deliberations: [],
      provider_mode: "local",
      verifier_status: null,
      duration_ms: 1.2,
    },
  ],
  audit_log: [
    {
      sequence: 1,
      state: "RESOLVE_CONCEPT",
      agent: "ConceptResolverAgent",
      summary: "Resolved Certification Ready.",
      status: "completed",
    },
  ],
};

const courtTranscript: DeliberationTranscript = {
  schema_version: "2.0",
  source_run_id: learningCase.run_id,
  term: "Certification Ready",
  concept_id: "certification_ready",
  verdict: "conflict",
  outcome: "proposal",
  authority_status: "clear",
  authority_owner: "Learning Governance Council",
  source_evidence_ids: learningCase.evidence.map((item) => item.evidence_id),
  rounds: 10,
  mode: "deterministic_fallback",
  captured_at: "2026-06-14T00:00:00Z",
  content_digest: "court-digest",
  framework: "Microsoft Agent Framework",
  workflow_trace: [
    "CourtCoordinatorAgent",
    "StewardPanelAgent",
    "InvestigatorPlanAgent",
    "EvidenceReviewAgent",
    "InvestigatorReplanAgent",
    "SkepticAgent",
    "StewardResponseAgent",
    "ReflectionAgent",
    "AuthorityAgent",
    "CourtAuditAgent",
  ],
  turns: [
    {
      turn_no: 1,
      round_no: 0,
      agent_id: "CourtCoordinatorAgent",
      role: "orchestrator",
      disposition: "asserted",
      speaking_for: null,
      content: "The court is convened over the frozen run.",
      tool_calls: [],
      cited_evidence_ids: [],
      provenance: {
        generated: false,
        provider_name: "DisabledLLMProvider",
        model: null,
        fallback_reason: "LLM narration is disabled.",
      },
    },
    {
      turn_no: 2,
      round_no: 6,
      agent_id: "StewardAgent.learning",
      role: "steward",
      disposition: "defended",
      speaking_for: "Learning & Development",
      content: "L&D defends the candidate while authority retains approval.",
      tool_calls: [],
      cited_evidence_ids: [evidenceIds[1]],
      provenance: {
        generated: false,
        provider_name: "DisabledLLMProvider",
        model: null,
        fallback_reason: "LLM narration is disabled.",
      },
    },
  ],
};

function mockJson(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

describe("learning-first Concord IQ experience", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const url = String(input);
        if (url.endsWith("/runtime")) {
          return mockJson({
            scenario_pack: "learning",
            runtime_profile: "local",
            switching_enabled: true,
            scenario_packs: [
              {
                id: "learning",
                label: "Learning",
                enabled: true,
                detail: "Learning pack.",
              },
              {
                id: "business",
                label: "Business",
                enabled: false,
                detail: "Disabled by configuration.",
              },
            ],
            runtime_profiles: [
              {
                id: "local",
                label: "Local Deterministic",
                available: true,
                cloud: false,
                detail: "Cloud-free synthetic fallback.",
                supported_packs: ["learning", "business"],
              },
            ],
          });
        }
        if (url.endsWith("/health")) {
          return mockJson({
            status: "ok",
            workflow_mode: "strict",
            provider: "LocalProvider",
            cloud_enabled: false,
            data_type: "synthetic",
            llm_provider: "DisabledLLMProvider",
            llm_enabled: false,
            llm_model: null,
            scenario_pack: "learning",
          });
        }
        if (url.endsWith("/demo/scenarios")) {
          return mockJson([scenario]);
        }
        if (url.endsWith("/proof/learning-scale")) {
          return mockJson({
            canonical_term: "Certification Ready",
            entity_type: "CertificationReady",
            learner_count: 10000,
            certification_ready_count: 522,
            false_ready_blocked_count: 4334,
            proof_kind: "fabric_bound_scale_artifact",
            execution_separation:
              "Separate from the 120-learner deterministic workbench execution.",
          });
        }
        if (url.endsWith("/demo/run/certification-ready")) {
          return mockJson(learningCase);
        }
        if (url.endsWith(`/runs/${learningCase.run_id}/court`)) {
          return mockJson(courtTranscript);
        }
        return mockJson({});
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

  it("defaults to Certification Ready and shows the false-readiness proof", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /False Readiness Firewall/i }),
    ).toBeInTheDocument();
    const option = within(screen.getByRole("list")).getByRole("button", {
      name: /Certification Ready/i,
    });
    expect(option).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTitle("Disabled by configuration.")).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));

    expect(await screen.findByText("Material conflict confirmed")).toBeInTheDocument();
    const summary = screen.getByLabelText("Certification readiness outcome");
    expect(within(summary).getByText("Claimed ready")).toBeInTheDocument();
    expect(within(summary).getByText("Verified ready")).toBeInTheDocument();
    expect(within(summary).getByText("False-ready learners")).toBeInTheDocument();
    expect(within(summary).getByText("Exam spend at risk")).toBeInTheDocument();
    expect(within(summary).getByText("80")).toBeInTheDocument();
    expect(within(summary).getByText("56")).toBeInTheDocument();
    expect(within(summary).getByText("24")).toBeInTheDocument();
    expect(screen.getByText("$10,800")).toBeInTheDocument();
    expect(screen.getByText("10,000")).toBeInTheDocument();
    expect(screen.getByText("4,334")).toBeInTheDocument();
    expect(
      screen.getByText(/not the source of the workbench’s 80\/56\/56 result/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Evidence workflow complete" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No SQL rerun. No new verdict. No duplicate proposal."),
    ).toBeInTheDocument();
    expect(screen.getByText(falseReadyIds.join(", "))).toBeInTheDocument();
    expect(screen.getAllByText("Learning Governance Council").length).toBeGreaterThan(0);
    expect(screen.getByText("Proposed canonical definition")).toBeInTheDocument();
    expect(screen.getByText("Skeptical verifier passed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /convene the court/i }));
    expect(
      await screen.findByRole("heading", { name: "Semantic Court over frozen run" }),
    ).toBeInTheDocument();
    expect(screen.getByText("L&D defends the candidate while authority retains approval."))
      .toBeInTheDocument();
  });

  it("shows a friendly Court API detail instead of raw JSON", async () => {
    const original = vi.mocked(fetch).getMockImplementation();
    vi.mocked(fetch).mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith(`/runs/${learningCase.run_id}/court`)) {
        return Promise.resolve({
          ok: false,
          status: 404,
          text: () =>
            Promise.resolve(
              JSON.stringify({
                detail: "Run the reconciliation again before convening the court.",
              }),
            ),
        } as Response);
      }
      return original!(input, init);
    });
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: /False Readiness Firewall/i });
    await user.click(screen.getByRole("button", { name: /analyze disagreement/i }));
    await screen.findByText("Material conflict confirmed");
    await user.click(screen.getByRole("button", { name: /convene the court/i }));

    expect(
      await screen.findByText("Run the reconciliation again before convening the court."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/"detail"/)).not.toBeInTheDocument();
  });
});
