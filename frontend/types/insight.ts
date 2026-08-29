import type { ConfidenceLevel } from "./persona";

export type InsightCategory =
  | "strength"
  | "objection"
  | "confusion"
  | "feature_request"
  | "uncertainty"
  | "disagreement";

export type VariantScope = "A" | "B" | "both";

export interface Insight {
  id: number;
  experiment_id: number;
  category: InsightCategory;
  variant_scope: VariantScope;
  title: string;
  summary: string;
  frequency: number;
  persona_count: number;
  supporting_run_ids: number[];
  supporting_evidence_ids: number[];
  confidence_level: ConfidenceLevel;
  prompt_version: string;
  model_name: string;
  created_at: string;
}

export interface InsightGenerateResponse {
  experiment_id: number;
  prompt_version: string;
  model_name: string;
  insight_count: number;
  insights: Insight[];
}

export const INSIGHT_CONTEXT_CHAR_LIMIT = 30_000;
