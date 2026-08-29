import type { EvidenceReference } from "./persona";

export type SimulationRunStatus = "completed" | "failed";

export type TaskOutcome = "completed" | "partially_completed" | "failed" | "uncertain";

export type FailureType =
  | "configuration_error"
  | "context_limit"
  | "timeout"
  | "rate_limit"
  | "provider_error"
  | "empty_output"
  | "malformed_json"
  | "invalid_schema"
  | "invalid_evidence_reference"
  | "unexpected_error";

export interface SimulationRun {
  id: number;
  experiment_id: number;
  variant_id: number;
  persona_id: number;
  repetition_index: number;
  status: SimulationRunStatus;
  task_outcome: TaskOutcome | null;
  clarity_score: number | null;
  perceived_value_score: number | null;
  adoption_intent_score: number | null;
  response_summary: string | null;
  positive_signals: string[];
  objections: string[];
  confusion_points: string[];
  feature_requests: string[];
  uncertainty_notes: string[];
  evidence_references: EvidenceReference[];
  prompt_version: string;
  model_name: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  estimated_cost_usd: string | null;
  failure_type: FailureType | null;
  failure_message: string | null;
  created_at: string;
  completed_at: string | null;
}
