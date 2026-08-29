export type Recommendation = "proceed" | "iterate" | "stop";

export interface RealUserTestPlan {
  objective: string;
  target_participants: string[];
  method: string;
  sample_size_rationale: string;
  tasks_or_questions: string[];
  success_metrics: string[];
  stopping_rule: string;
}

export interface DecisionMemo {
  id: number;
  experiment_id: number;
  recommendation: Recommendation;
  executive_summary: string;
  supporting_findings: string[];
  weakest_assumptions: string[];
  recommended_product_changes: string[];
  risks: string[];
  uncertain_conclusions: string[];
  recommended_success_metrics: string[];
  real_user_test: RealUserTestPlan;
  supporting_insight_ids: number[];
  prompt_version: string;
  model_name: string;
  created_at: string;
  updated_at: string;
}
