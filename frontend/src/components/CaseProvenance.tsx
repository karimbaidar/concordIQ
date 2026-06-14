import type { ReconciliationCase } from "../types";

interface CaseProvenanceProps {
  result: ReconciliationCase;
  runtimeProfile?: string;
}

function provenanceText(result: ReconciliationCase, runtimeProfile?: string) {
  const metadata = result.context_packet?.provider_metadata;
  if (!metadata) {
    return "Provider provenance unavailable.";
  }
  if (metadata.mode === "foundry_hosted") {
    return "Foundry-hosted Agent Framework execution over a verified sanitized Fabric replay.";
  }
  if (metadata.grounding_kind === "fabric_ontology_match") {
    return "Fabric IQ matched the governed ontology concept; deterministic local snapshot SQL produced the displayed populations.";
  }
  if (metadata.grounding_kind === "local_registry_fallback") {
    return "This governed supporting scenario used the deterministic local registry; Fabric IQ did not ground this term.";
  }
  if (metadata.mode === "local" && runtimeProfile === "fabric_live") {
    return "This supporting scenario used the deterministic local registry; the verified live Fabric ontology currently grounds Certification Ready only.";
  }
  if (metadata.mode === "local" && runtimeProfile === "foundry_live") {
    return "This supporting scenario used the deterministic local registry; the verified Foundry Agent Service deployment currently hosts Certification Ready only.";
  }
  if (metadata.grounding_kind === "sanitized_fabric_replay" || metadata.mode === "replay") {
    return "Sanitized Fabric IQ capture replay; deterministic replay SQL produced the displayed populations with no cloud call.";
  }
  return "Deterministic local registry execution over synthetic data.";
}

export function CaseProvenance({ result, runtimeProfile }: CaseProvenanceProps) {
  return (
    <aside className="case-provenance" aria-label="Case execution provenance">
      <strong>How this case was produced</strong>
      <span>{provenanceText(result, runtimeProfile)}</span>
    </aside>
  );
}
