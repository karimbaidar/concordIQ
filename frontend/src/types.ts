export type Verdict = "conflict" | "consistent" | "incomplete";
export type Severity = "low" | "medium" | "high";

export interface HealthStatus {
  status: string;
  provider: string;
  cloud_enabled: boolean;
  data_type: string;
}

export interface DemoScenario {
  scenario_id: string;
  term: string;
  question: string;
}

export interface EvaluationPeriod {
  start_date: string;
  end_date: string;
}

export interface DefinitionBinding {
  binding_id: string;
  definition_id: string;
  concept_id: string;
  name: string;
  owner: string;
  rule_text: string;
  semantic_dimensions: string[];
  source_tables: string[];
  entity_key: string;
  grain: string;
  population: string;
  time_window_days: number | null;
  filters: string[];
  exclusions: string[];
  sql_template: string;
}

export interface DefinitionEvaluation {
  binding_id: string;
  definition_id: string;
  concept_id: string;
  period: EvaluationPeriod;
  entity_ids: string[];
  rows: Array<{ entity_id: string; metric_value: number }>;
  entity_count: number;
  metric_total: number;
  executed_sql: string;
}

export interface TimelineEntry {
  sequence: number;
  state: string;
  agent: string;
  summary: string;
  status: "completed" | "failed";
}

export interface ImpactAssessment {
  rank: number;
  severity: Severity;
  customer_count_delta: number;
  arr_delta: number;
  reports_affected: number;
  business_units_affected: string[];
  decision_criticality: Severity;
}

export interface AuthorityRule {
  concept_id: string;
  semantic_dimension: string;
  status: string;
  owner: string | null;
  rationale: string;
}

export interface AuthorityAssessment {
  status: "clear" | "shared" | "ambiguous" | "missing";
  owner: string | null;
  rules: AuthorityRule[];
  rationale: string;
}

export interface EvidenceRecord {
  evidence_id: string;
  binding_id: string;
  definition_id: string;
  source_ref: string;
  entity_count: number;
  metric_total: number;
  entity_ids: string[];
  sql_text: string;
}

export interface ReconciliationProposal {
  canonical_definition: string;
  rationale: string;
  migration_notes: string[];
  expected_dashboard_impact: string;
  authority_owner: string;
  requires_human_approval: boolean;
  evidence_refs: string[];
}

export interface VerifierReport {
  passed: boolean;
  checks: Record<string, boolean>;
  failures: string[];
  advisory_notes: string[];
}

export interface ReconciliationCase {
  run_id: string;
  request: {
    question: string;
    term: string;
    period: EvaluationPeriod;
  };
  state: string;
  context_packet: {
    provider_metadata: {
      name: string;
      mode: string;
      uses_cloud: boolean;
      data_type: string;
    };
    active_scenario: string;
  } | null;
  resolved_concept: {
    concept_id: string;
    canonical_name: string;
    description: string;
    aliases: string[];
    definition_ids: string[];
  } | null;
  binding_semantics: DefinitionBinding[];
  execution_results: DefinitionEvaluation[];
  verdict: Verdict;
  impact_assessment: ImpactAssessment | null;
  authority_assessment: AuthorityAssessment | null;
  reconciliation_proposal: ReconciliationProposal | null;
  refusal_reason: string | null;
  requires_human_approval: boolean;
  verifier_report: VerifierReport | null;
  evidence: EvidenceRecord[];
  audit_log: TimelineEntry[];
}
