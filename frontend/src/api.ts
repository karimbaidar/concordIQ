import type { DemoScenario, HealthStatus, ReconciliationCase } from "./types";

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
