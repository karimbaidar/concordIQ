export type Verdict = "conflict" | "consistent" | "incomplete";
export type Severity = "low" | "medium" | "high";

export interface HealthStatus {
  status: string;
  workflow_mode: "fast" | "strict";
  provider: string;
  provider_mode?: string;
  runtime?: string;
  cloud_enabled: boolean;
  data_type: string;
  llm_provider: string;
  llm_enabled: boolean;
  llm_model: string | null;
  scenario_pack?: "learning" | "business";
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

export interface WhatIfMetric {
  entity_count: number;
  metric_value: number;
}

export interface WhatIfResult {
  term: string;
  binding_id: string;
  overrides: {
    time_window_days: number;
  };
  baseline: WhatIfMetric;
  whatif: WhatIfMetric;
  delta: WhatIfMetric;
  sql: string;
  ephemeral: true;
  note: string;
}

export interface TimelineEntry {
  sequence: number;
  state: string;
  agent: string;
  summary: string;
  status: "completed" | "failed";
}

export interface ConflictHypothesis {
  left_binding_id: string;
  right_binding_id: string;
  differing_dimensions: string[];
  rationale: string;
  claim: string;
  skeptic_challenge: string;
  data_verdict: "pending" | "confirmed" | "overturned";
  evidence_ids: string[];
}

export interface AgentTraceStep {
  step_number: number;
  agent_name: string;
  input_summary: string;
  output_summary: string;
  evidence_ids: string[];
  deliberations: ConflictHypothesis[];
  provider_mode: string;
  verifier_status: "pending" | "passed" | "needs_review" | "blocked" | null;
  duration_ms: number | null;
}

export interface ImpactAssessment {
  rank: number;
  severity: Severity;
  customer_count_delta: number;
  arr_delta: number;
  reports_affected: number;
  business_units_affected: string[];
  decision_criticality: Severity;
  entity_label?: string;
  value_label?: string;
  affected_entity_ids?: string[];
  false_positive_count?: number | null;
  false_positive_label?: string | null;
  false_positive_entity_ids?: string[];
}

export interface AuthorityRule {
  concept_id: string;
  semantic_dimension: string;
  status: string;
  owner: string | null;
  rationale: string;
}

export interface AuthorityGrounding {
  source: string;
  retrieved_owner: string | null;
  citation: string;
  note: string;
  agrees_with_rule: boolean;
  advisory_only: boolean;
}

export interface AuthorityAssessment {
  status: "clear" | "shared" | "ambiguous" | "missing";
  owner: string | null;
  rules: AuthorityRule[];
  rationale: string;
  advisory_grounding?: AuthorityGrounding | null;
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
  canonical_source_definition_id?: string | null;
}

export interface GovernedCanonical {
  canonical_definition_id: string;
  version: string;
  rule_text: string;
  source_definition_id: string;
  approved_by: string;
  approved_at: string;
  approving_run_id: string;
  registry_scope: "concord_iq";
  domain_views: DefinitionBinding[];
}

export interface VerifierReport {
  passed: boolean;
  checks: Record<string, boolean>;
  failures: string[];
  attempt: number;
  recoverable: boolean;
  recovery_stage:
    | "execute_definitions"
    | "rank_impact"
    | "resolve_authority"
    | "reconcile_or_refuse"
    | null;
  advisory_notes: string[];
  narration: NarrationResult | null;
}

export interface NarrationResult {
  task: "decision" | "verifier" | "audit";
  text: string;
  provider_name: string;
  model: string | null;
  generated: boolean;
  fallback_reason: string | null;
}

export type RecommendedAction = "propose" | "refuse" | "monitor";

export interface PortfolioConceptResult {
  rank: number;
  concept_id: string;
  term: string;
  verdict: "conflict" | "consistent";
  definition_count: number;
  counts: number[];
  owners: string[];
  customer_count_delta: number;
  arr_delta: number;
  severity: Severity;
  authority_status: "clear" | "shared" | "ambiguous" | "missing";
  authority_owner: string | null;
  recommended_action: RecommendedAction;
}

export interface BusinessUnitScore {
  business_unit: string;
  score: number;
  open_conflicts: number;
}

export interface ConcordScore {
  overall: number;
  grade: "A" | "B" | "C" | "D" | "F";
  concepts_scanned: number;
  conflicts: number;
  consistent: number;
  refusals: number;
  by_business_unit: BusinessUnitScore[];
}

export interface PortfolioScan {
  generated_at: string;
  provider: string;
  period: EvaluationPeriod;
  score: ConcordScore;
  concepts: PortfolioConceptResult[];
}

export interface QueryDefinitionSummary {
  definition_id: string;
  name: string;
  owner: string;
  rule_text: string;
}

export interface QueryResult {
  question: string;
  matched: boolean;
  grounding_provider: string;
  concept_id: string | null;
  canonical_name: string | null;
  answer: string;
  definitions: QueryDefinitionSummary[];
  citations: string[];
}

export interface AskResponse {
  query: QueryResult;
  case: ReconciliationCase | null;
}

export interface UngovernedTermRefusal {
  refused: true;
  term: string;
  reason: string;
  known_terms: string[];
}

export interface ProposalDecisionResult {
  run_id: string;
  term: string;
  status: "approved" | "rejected";
  authority_owner: string;
  decided_by: string;
  decided_at: string;
  canonical_definition_id: string | null;
  canonical_version: string | null;
  canonical_source_definition_id: string | null;
  registry_scope: "concord_iq" | null;
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
      runtime?: string;
      semantic_provider?: {
        name?: string;
        mode?: string;
      };
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
  conflict_hypotheses: ConflictHypothesis[];
  execution_results: DefinitionEvaluation[];
  verdict: Verdict;
  verification_status: "pending" | "passed" | "needs_review" | "blocked";
  verifier_attempts: number;
  verification_recovery:
    | "execute_definitions"
    | "rank_impact"
    | "resolve_authority"
    | "reconcile_or_refuse"
    | null;
  impact_assessment: ImpactAssessment | null;
  authority_assessment: AuthorityAssessment | null;
  governed_canonical: GovernedCanonical | null;
  reconciliation_proposal: ReconciliationProposal | null;
  refusal_reason: string | null;
  requires_human_approval: boolean;
  verifier_report: VerifierReport | null;
  narrations: NarrationResult[];
  evidence: EvidenceRecord[];
  agent_trace: AgentTraceStep[];
  audit_log: TimelineEntry[];
}
