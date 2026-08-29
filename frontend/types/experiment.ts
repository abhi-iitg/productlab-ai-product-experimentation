export type ExperimentStatus =
  | "draft"
  | "running"
  | "completed"
  | "partially_completed"
  | "failed";

export type VariantKey = "A" | "B";

export interface Variant {
  id: number;
  experiment_id: number;
  key: VariantKey;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface VariantInput {
  key: VariantKey;
  name: string;
  description: string;
}

export interface Experiment {
  id: number;
  project_id: number;
  name: string;
  objective: string;
  hypothesis: string;
  scenario: string;
  evaluation_criteria: string[];
  repeat_count: number;
  status: ExperimentStatus;
  persona_ids: number[];
  variants: Variant[];
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ExperimentCreateInput {
  name: string;
  objective: string;
  hypothesis: string;
  scenario: string;
  evaluation_criteria: string[];
  repeat_count: number;
  persona_ids: number[];
  variants: VariantInput[];
}

export interface ExperimentUpdateInput {
  name?: string;
  objective?: string;
  hypothesis?: string;
  scenario?: string;
  evaluation_criteria?: string[];
  repeat_count?: number;
  persona_ids?: number[];
  variants?: VariantInput[];
}

export interface ExperimentExecutionSummary {
  project_id: number;
  experiment_id: number;
  status: ExperimentStatus;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  prompt_version: string;
  model_name: string;
  started_at: string | null;
  completed_at: string | null;
}

export const MAX_SIMULATION_RUNS = 30;
