import type { HealthStatus, ReconciliationCase } from "../types";

interface ProviderBadgeProps {
  health: HealthStatus | null;
  result: ReconciliationCase | null;
}

export function ProviderBadge({ health, result }: ProviderBadgeProps) {
  const metadata = result?.context_packet?.provider_metadata;
  const provider = metadata?.name ?? health?.provider ?? "Connecting";
  const mode = metadata?.mode ?? health?.provider_mode ?? "local";
  const hostedRuntime = metadata
    ? mode === "foundry_hosted"
    : mode === "foundry_hosted" || health?.runtime === "Foundry Agent Service";
  const modeLabel = hostedRuntime ? "hosted runtime" : `${mode} mode`;
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
        <small className="provider-mode">{modeLabel}</small>
        <small className="runtime-summary">
          {modeLabel} · {cloudEnabled ? "cloud enabled" : "cloud disabled"} · {llmLabel}
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
