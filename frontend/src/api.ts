import type {
  AskResponse,
  DeliberationTranscript,
  DemoScenario,
  HealthStatus,
  LearningScaleProof,
  PortfolioScan,
  ProposalDecisionResult,
  ReconciliationCase,
  RuntimeProfile,
  RuntimeState,
  ScenarioPack,
  UngovernedTermRefusal,
  WhatIfResult,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

interface StructuredErrorDetail {
  code?: string;
  title?: string;
  message?: string;
  recovery_profile?: RuntimeProfile;
  recovery_label?: string;
}

export class ConcordApiError extends Error {
  status: number;
  code: string | null;
  title: string | null;
  recoveryProfile: RuntimeProfile | null;
  recoveryLabel: string | null;

  constructor(
    message: string,
    status: number,
    detail: StructuredErrorDetail | null = null,
  ) {
    super(message);
    this.name = "ConcordApiError";
    this.status = status;
    this.code = detail?.code ?? null;
    this.title = detail?.title ?? null;
    this.recoveryProfile = detail?.recovery_profile ?? null;
    this.recoveryLabel = detail?.recovery_label ?? null;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const raw = await response.text();
    let detail = raw;
    let structured: StructuredErrorDetail | null = null;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        detail = parsed.detail;
      } else if (
        typeof parsed.detail === "object" &&
        parsed.detail !== null &&
        "message" in parsed.detail
      ) {
        structured = parsed.detail as StructuredErrorDetail;
        detail = structured.message ?? `Request failed with status ${response.status}.`;
      } else if (Array.isArray(parsed.detail)) {
        const messages = parsed.detail
          .map((item) => {
            if (typeof item === "object" && item !== null && "msg" in item) {
              return String(item.msg);
            }
            return null;
          })
          .filter((item): item is string => item !== null);
        detail =
          messages.join(" ") || `Request failed with status ${response.status}.`;
      } else {
        detail = `Request failed with status ${response.status}.`;
      }
    } catch {
      // Preserve plain-text errors from non-FastAPI intermediaries.
    }
    throw new ConcordApiError(
      detail || `Request failed with status ${response.status}.`,
      response.status,
      structured,
    );
  }
  return response.json() as Promise<T>;
}

export function fetchHealth(): Promise<HealthStatus> {
  return requestJson<HealthStatus>("/health");
}

export function fetchRuntimeState(): Promise<RuntimeState> {
  return requestJson<RuntimeState>("/runtime");
}

export function selectRuntime(
  scenarioPack: ScenarioPack,
  runtimeProfile: RuntimeProfile,
): Promise<RuntimeState> {
  return requestJson<RuntimeState>("/runtime/select", {
    method: "POST",
    body: JSON.stringify({
      scenario_pack: scenarioPack,
      runtime_profile: runtimeProfile,
    }),
  });
}

export function fetchDemoScenarios(): Promise<DemoScenario[]> {
  return requestJson<DemoScenario[]>("/demo/scenarios");
}

export function runDemoScenario(scenarioId: string): Promise<ReconciliationCase> {
  return requestJson<ReconciliationCase>(`/demo/run/${scenarioId}`, {
    method: "POST",
  });
}

export function runCourt(runId: string): Promise<DeliberationTranscript> {
  return requestJson<DeliberationTranscript>(`/runs/${runId}/court`, {
    method: "POST",
  });
}

export function runGovernedRerun(runId: string): Promise<ReconciliationCase> {
  return requestJson<ReconciliationCase>(`/runs/${runId}/governed-rerun`, {
    method: "POST",
  });
}

export function fetchLearningScaleProof(): Promise<LearningScaleProof> {
  return requestJson<LearningScaleProof>("/proof/learning-scale");
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
