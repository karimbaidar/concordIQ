import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { DeliberationTranscript, DeliberationTurn } from "../types";
import { CourtTimeline } from "./CourtTimeline";

afterEach(cleanup);

function turn(partial: Partial<DeliberationTurn> & Pick<DeliberationTurn, "turn_no" | "role">) {
  return {
    round_no: 0,
    agent_id: partial.role,
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
    schema_version: "1.0",
    term: "Certification Ready",
    concept_id: "certification_ready",
    verdict: "conflict",
    outcome: "proposal",
    rounds: 8,
    mode: "replayed",
    captured_at: "2026-06-14T00:00:00Z",
    content_digest: "abc123",
    turns: [
      turn({ turn_no: 1, role: "orchestrator", round_no: 0, content: "The court is convened." }),
      turn({
        turn_no: 2,
        role: "steward",
        round_no: 1,
        speaking_for: "HR",
        content: "For HR: 80 are ready.",
        tool_calls: ["executed_sql:certification_ready_hr_v1"],
        cited_evidence_ids: ["e1"],
      }),
      turn({
        turn_no: 3,
        role: "investigator",
        round_no: 2,
        content: "Executed. 24 learners are claimed ready but blocked.",
      }),
      turn({ turn_no: 4, role: "skeptic", round_no: 3, content: "Cross-examination of HR." }),
      turn({ turn_no: 5, role: "authority", round_no: 6, content: "Authority is clear." }),
    ],
    ...overrides,
  };
}

describe("CourtTimeline", () => {
  it("renders the debate with every role and the honest replay badge", () => {
    render(<CourtTimeline transcript={transcript()} />);

    expect(screen.getByText("The Semantic Court")).toBeInTheDocument();
    expect(screen.getByText("Replay · captured debate")).toBeInTheDocument();
    expect(screen.getByText("Orchestrator")).toBeInTheDocument();
    expect(screen.getByText("Steward")).toBeInTheDocument();
    expect(screen.getByText("Investigator")).toBeInTheDocument();
    expect(screen.getByText("Skeptic")).toBeInTheDocument();
    expect(screen.getByText("Authority")).toBeInTheDocument();
    expect(screen.getByText("for HR")).toBeInTheDocument();
    expect(
      screen.getByText("executed_sql:certification_ready_hr_v1"),
    ).toBeInTheDocument();
  });

  it("shows the governed-proposal ruling", () => {
    render(<CourtTimeline transcript={transcript()} />);
    expect(
      screen.getByText("Governed proposal — human approval required"),
    ).toBeInTheDocument();
  });

  it("labels a live model turn and a refusal ruling", () => {
    render(
      <CourtTimeline
        transcript={transcript({
          mode: "live_captured",
          outcome: "refusal",
          turns: [
            turn({
              turn_no: 1,
              role: "authority",
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

    expect(screen.getByText("Live · model-generated")).toBeInTheDocument();
    expect(screen.getByText("live")).toBeInTheDocument();
    expect(
      screen.getByText("Refused — routed to a human, minority report recorded"),
    ).toBeInTheDocument();
  });
});
