import type { ExperimentStatus, VariantKey } from "./experiment";
import type { FailureType } from "./simulation-run";

export interface TaskOutcomeDistribution {
  completed: number;
  partially_completed: number;
  failed: number;
  uncertain: number;
}

export interface ThemeCounts {
  positive_signals: number;
  objections: number;
  confusion_points: number;
  feature_requests: number;
  uncertainty_notes: number;
}

export interface VariantMetrics {
  variant_id: number;
  variant_key: VariantKey;
  completed_run_count: number;
  failed_run_count: number;
  task_outcome_distribution: TaskOutcomeDistribution;
  task_completion_rate: number | null;
  average_clarity_score: number | null;
  average_perceived_value_score: number | null;
  average_adoption_intent_score: number | null;
  average_latency_ms: number | null;
  total_input_tokens: number;
  total_output_tokens: number;
  total_estimated_cost_usd: string | null;
}

export interface ExperimentCoverage {
  expected_runs: number;
  total_persisted_runs: number;
  completed_runs: number;
  failed_runs: number;
  completion_rate: number | null;
  represented_persona_count: number;
  data_quality_warnings: string[];
}

export interface EvidenceCoverage {
  completed_runs_with_evidence: number;
  completed_runs_total: number;
  evidence_citation_rate: number | null;
  unique_cited_evidence_ids: number[];
}

export interface FailureBreakdown {
  counts_by_category: Partial<Record<FailureType, number>>;
  total_failed_runs: number;
}

export interface PersonaScoreProfile {
  average_clarity_score: number;
  average_perceived_value_score: number;
  average_adoption_intent_score: number;
}

export interface PersonaDisagreement {
  persona_id: number;
  variant_a_scores: PersonaScoreProfile;
  variant_b_scores: PersonaScoreProfile;
  direction: string;
  diverges_from_overall_variant_direction: boolean;
}

export interface DataQualityFlags {
  variant_a_zero_completed_runs: boolean;
  variant_b_zero_completed_runs: boolean;
  severe_failure_imbalance: boolean;
  insufficient_persona_coverage: boolean;
  no_evidence_citations: boolean;
}

export interface AnalyticsResponse {
  experiment_id: number;
  experiment_status: ExperimentStatus;
  coverage: ExperimentCoverage;
  variant_metrics: VariantMetrics[];
  deterministic_theme_counts: Partial<Record<VariantKey, ThemeCounts>>;
  failure_breakdown: FailureBreakdown;
  evidence_coverage: EvidenceCoverage;
  persona_disagreement: PersonaDisagreement[];
  data_quality_warnings: string[];
  data_quality_flags: DataQualityFlags;
}
