import type { ExperimentStatus, VariantKey } from "./experiment";
import type { TaskOutcome } from "./simulation-run";
import type { TaskOutcomeDistribution } from "./analytics";

export type SourceMethod = "interview" | "usability_test" | "survey" | "observation" | "other";

export interface HumanFeedback {
  id: number;
  experiment_id: number;
  participant_label: string;
  variant_key: VariantKey;
  task_outcome: TaskOutcome;
  clarity_score: number;
  perceived_value_score: number;
  adoption_intent_score: number;
  feedback_summary: string;
  positive_signals: string[];
  objections: string[];
  confusion_points: string[];
  feature_requests: string[];
  uncertainty_notes: string[];
  source_method: SourceMethod;
  session_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface HumanFeedbackCreateInput {
  participant_label: string;
  variant_key: VariantKey;
  source_method: SourceMethod;
  session_date?: string | null;
  task_outcome: TaskOutcome;
  clarity_score: number;
  perceived_value_score: number;
  adoption_intent_score: number;
  feedback_summary: string;
  positive_signals?: string[];
  objections?: string[];
  confusion_points?: string[];
  feature_requests?: string[];
  uncertainty_notes?: string[];
}

export interface HumanFeedbackUpdateInput {
  participant_label?: string;
  variant_key?: VariantKey;
  source_method?: SourceMethod;
  session_date?: string | null;
  task_outcome?: TaskOutcome;
  clarity_score?: number;
  perceived_value_score?: number;
  adoption_intent_score?: number;
  feedback_summary?: string;
  positive_signals?: string[];
  objections?: string[];
  confusion_points?: string[];
  feature_requests?: string[];
  uncertainty_notes?: string[];
}

export type QualitativeCategory =
  | "positive_signals"
  | "objections"
  | "confusion_points"
  | "feature_requests"
  | "uncertainty_notes";

export type MetricName = "clarity" | "perceived_value" | "adoption_intent";

export type DirectionValue = "A_higher" | "B_higher" | "equal" | "insufficient_data";

export type AlignmentValue = "aligned" | "not_aligned" | "insufficient_data";

export interface SyntheticVariantSummary {
  variant_key: VariantKey;
  completed_run_count: number;
  represented_persona_count: number;
  task_outcome_distribution: TaskOutcomeDistribution;
  average_clarity_score: number | null;
  average_perceived_value_score: number | null;
  average_adoption_intent_score: number | null;
  positive_signals: string[];
  objections: string[];
  confusion_points: string[];
  feature_requests: string[];
  uncertainty_notes: string[];
}

export interface HumanVariantSummary {
  variant_key: VariantKey;
  feedback_record_count: number;
  unique_participant_count: number;
  task_outcome_distribution: TaskOutcomeDistribution;
  average_clarity_score: number | null;
  average_perceived_value_score: number | null;
  average_adoption_intent_score: number | null;
  positive_signals: string[];
  objections: string[];
  confusion_points: string[];
  feature_requests: string[];
  uncertainty_notes: string[];
}

export interface VariantComparison {
  variant_key: VariantKey;
  synthetic: SyntheticVariantSummary;
  human: HumanVariantSummary;
}

export interface VariantThemeComparison {
  variant_key: VariantKey;
  category: QualitativeCategory;
  shared_themes: string[];
  synthetic_only_themes: string[];
  human_only_themes: string[];
}

export interface MetricDirectionComparison {
  metric: MetricName;
  synthetic_direction: DirectionValue;
  human_direction: DirectionValue;
  alignment: AlignmentValue;
}

export interface TaskOutcomeComparison {
  variant_key: VariantKey;
  synthetic_completion_rate: number | null;
  human_completion_rate: number | null;
  absolute_difference: number | null;
}

export interface HumanComparisonResponse {
  project_id: number;
  experiment_id: number;
  experiment_status: ExperimentStatus;
  synthetic_summary: SyntheticVariantSummary[];
  human_summary: HumanVariantSummary[];
  variant_comparisons: VariantComparison[];
  theme_comparisons: VariantThemeComparison[];
  metric_direction_comparisons: MetricDirectionComparison[];
  task_outcome_comparisons: TaskOutcomeComparison[];
  shared_theme_count: number;
  synthetic_only_theme_count: number;
  human_only_theme_count: number;
  data_quality_warnings: string[];
  interpretation_notice: string;
}
