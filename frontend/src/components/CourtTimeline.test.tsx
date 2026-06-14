import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { DeliberationTranscript, DeliberationTurn } from "../types";
import { CourtTimeline } from "./CourtTimeline";

afterEach(cleanup);

function turn(partial: Partial<DeliberationTurn> & Pick<DeliberationTurn, "turn_no" | "role">) {
  return {
    round_no: 0,
    agent_id: partial.role,
    disposition: "asserted",
    speaking_for: null,
    content: "",
    tool_calls: [],
    cited_evidence_ids: [],
    provenance: {
      generated: false,
      provider_name: "DisabledLLMProvider",
      model: null,
      fallback_reason: "LLM narration is disabled.",
    },
    ...partial,
  } as DeliberationTurn;
}

function transcript(overrides: Partial<DeliberationTranscript> = {}): DeliberationTranscript {
  return {
    schema_version: "2.0",
    source_run_id: "00000000-0000-0000-0000-000000000099",
    term: "Certification Ready",
    concept_id: "certification_ready",
    verdict: "conflict",
    outcome: "proposal",
    authority_status: "clear",
    authority_owner: "Learning Governance Council",
    source_evidence_ids: [
      "00000000-0000-0000-0000-000000000001",
      "00000000-0000-0000-0000-000000000002",
    ],
    rounds: 10,
    mode: "replayed",
    captured_at: "2026-06-14T00:00:00Z",
    content_digest: "abc123",
    framework: "Microsoft Agent Framework",
    workflow_trace: [
      "CourtCoordinatorAgent",
      "StewardPanelAgent",
      "InvestigatorPlanAgent",
      "EvidenceReviewAgent",
      "SkepticAgent",
      "AuthorityAgent",
      "CourtAuditAgent",
    ],
    turns: [
      turn({
        turn_no: 1,
        role: "orchestrator",
        agent_id: "CourtCoordinatorAgent",
        round_no: 0,
        content: "The court is convened.",
      }),
      turn({
        turn_no: 2,
        role: "steward",
        agent_id: "StewardAgent.hr",
        round_no: 1,
        speaking_for: "HR",
        disposition: "narrowed",
        content: "For HR: 80 are ready.",
        tool_calls: ["executed_sql:certification_ready_hr_v1"],
        cited_evidence_ids: ["e1"],
      }),
      turn({
        turn_no: 3,
        role: "investigator",
        agent_id: "EvidenceReviewAgent",
        round_no: 2,
        disposition: "confirmed",
        content: "Executed. 24 learners are claimed ready but blocked.",
      }),
      turn({
        turn_no: 4,
        role: "skeptic",
        agent_id: "SkepticAgent",
        round_no: 5,
        disposition: "challenged",
        content: "Cross-examination of HR.",
      }),
      turn({
        turn_no: 5,
        role: "authority",
        agent_id: "AuthorityAgent",
        round_no: 8,
        disposition: "confirmed",
        content: "Authority is clear.",
      }),
    ],
    ...overrides,
  };
}

describe("CourtTimeline", () => {
  it("renders the debate with every role and the honest replay badge", () => {
    render(<CourtTimeline transcript={transcript()} />);

    expect(screen.getByText("Semantic Court over frozen run")).toBeInTheDocument();
    expect(screen.getByText("Replay · captured Court")).toBeInTheDocument();
    expect(screen.getByText("StewardAgent.hr")).toBeInTheDocument();
    expect(screen.getAllByText("EvidenceReviewAgent").length).toBeGreaterThan(0);
    expect(screen.getAllByText("SkepticAgent").length).toBeGreaterThan(0);
    expect(screen.getAllByText("AuthorityAgent").length).toBeGreaterThan(0);
    expect(screen.getByText("for HR")).toBeInTheDocument();
    expect(screen.getByText("narrowed")).toBeInTheDocument();
    expect(
      screen.getByText("executed_sql:certification_ready_hr_v1"),
    ).toBeInTheDocument();
  });

  it("shows the governed-proposal ruling", () => {
    render(<CourtTimeline transcript={transcript()} />);
    expect(screen.getByText("Court audit").parentElement).toHaveTextContent(
      "Governed proposal preserved — human approval required",
    );
  });

  it("labels a live model turn and a refusal ruling", () => {
    render(
      <CourtTimeline
        transcript={transcript({
        mode: "live_captured",
        outcome: "refusal",
        authority_status: "ambiguous",
        authority_owner: null,
        turns: [
            turn({
              turn_no: 1,
              role: "authority",
              agent_id: "AuthorityAgent",
              disposition: "refused",
              content: "Authority is ambiguous; the court must refuse.",
              provenance: {
                generated: true,
                provider_name: "FoundryModel",
                model: "gpt",
                fallback_reason: null,
              },
            }),
          ],
        })}
      />,
    );

    expect(screen.getByText("Live · model-generated narration")).toBeInTheDocument();
    expect(screen.getByText("live narration")).toBeInTheDocument();
    expect(screen.getByText("Court audit").parentElement).toHaveTextContent(
      "Governance refusal preserved — routed to humans",
    );
  });
});
