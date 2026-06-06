import type { HealthStatus, ReconciliationCase } from "../types";

interface ProviderBadgeProps {
  health: HealthStatus | null;
  result: ReconciliationCase | null;
}

export function ProviderBadge({ health, result }: ProviderBadgeProps) {
  const metadata = result?.context_packet?.provider_metadata;
  const provider = metadata?.name ?? health?.provider ?? "Connecting";
  const mode = metadata?.mode ?? "local";
  const cloudEnabled = metadata?.uses_cloud ?? health?.cloud_enabled ?? false;
  const dataType = metadata?.data_type ?? health?.data_type ?? "synthetic";
  const llmLabel = health?.llm_enabled
    ? health.llm_model ?? health.llm_provider
    : "narration off";

  return (
    <div className="provider-badge" aria-label="Runtime status">
      <span className="status-dot" aria-hidden="true" />
      <span>
        <strong>{provider}</strong>
        <small className="provider-mode">{mode} mode</small>
        <small className="runtime-summary">
          {mode} · {cloudEnabled ? "cloud on" : "cloud off"} · {llmLabel}
        </small>
      </span>
      <span className="badge-divider" />
      <span>
        <strong>{cloudEnabled ? "Cloud enabled" : "Cloud disabled"}</strong>
        <small>{dataType} data</small>
      </span>
    </div>
  );
}
