import type {
  AskResponse,
  DemoScenario,
  HealthStatus,
  PortfolioScan,
  ProposalDecisionResult,
  ReconciliationCase,
  UngovernedTermRefusal,
  WhatIfResult,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

export function fetchHealth(): Promise<HealthStatus> {
  return requestJson<HealthStatus>("/health");
}

export function fetchDemoScenarios(): Promise<DemoScenario[]> {
  return requestJson<DemoScenario[]>("/demo/scenarios");
}

export function runDemoScenario(scenarioId: string): Promise<ReconciliationCase> {
  return requestJson<ReconciliationCase>(`/demo/run/${scenarioId}`, {
    method: "POST",
  });
}

export function fetchPortfolioScan(): Promise<PortfolioScan> {
  return requestJson<PortfolioScan>("/scan");
}

export function askConcord(question: string): Promise<AskResponse> {
  return requestJson<AskResponse>("/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function reconcileTerm(
  term: string,
): Promise<ReconciliationCase | UngovernedTermRefusal> {
  return requestJson<ReconciliationCase | UngovernedTermRefusal>("/analyze", {
    method: "POST",
    body: JSON.stringify({
      term,
      question: `Why do our ${term} definitions disagree?`,
    }),
  });
}

export function isUngovernedRefusal(
  value: ReconciliationCase | UngovernedTermRefusal,
): value is UngovernedTermRefusal {
  return (value as UngovernedTermRefusal).refused === true;
}

export function reconcileWhatIf(
  term: string,
  bindingId: string,
  timeWindowDays: number,
): Promise<WhatIfResult> {
  return requestJson<WhatIfResult>("/reconcile/whatif", {
    method: "POST",
    body: JSON.stringify({
      term,
      binding_id: bindingId,
      overrides: { time_window_days: timeWindowDays },
    }),
  });
}

export function decideProposal(
  runId: string,
  decision: "approve" | "reject",
  approver: string,
): Promise<ProposalDecisionResult> {
  return requestJson<ProposalDecisionResult>(`/proposals/${runId}/${decision}`, {
    method: "POST",
    body: JSON.stringify({ approver }),
  });
}
