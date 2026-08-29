export type ProjectStatus = "draft" | "active" | "archived";

export interface Project {
  id: number;
  name: string;
  problem_statement: string;
  target_user: string;
  product_hypothesis: string;
  success_metric: string;
  assumptions: string[];
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  problem_statement: string;
  target_user: string;
  product_hypothesis: string;
  success_metric: string;
  assumptions: string[];
  status?: ProjectStatus;
}

export interface ProjectUpdateInput {
  name?: string;
  problem_statement?: string;
  target_user?: string;
  product_hypothesis?: string;
  success_metric?: string;
  assumptions?: string[];
  status?: ProjectStatus;
}
