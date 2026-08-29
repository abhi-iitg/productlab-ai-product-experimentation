export type ConfidenceLevel = "low" | "medium" | "high";

export interface EvidenceReference {
  evidence_item_id: number;
  supported_claims: string[];
}

export interface Persona {
  id: number;
  project_id: number;
  name: string;
  segment_label: string;
  summary: string;
  goals: string[];
  pain_points: string[];
  constraints: string[];
  behaviors: string[];
  evidence_references: EvidenceReference[];
  unsupported_assumptions: string[];
  confidence_level: ConfidenceLevel;
  prompt_version: string;
  model_name: string;
  created_at: string;
  updated_at: string;
}

export interface PersonaGenerateInput {
  persona_count: number;
  selected_evidence_ids?: number[] | null;
  focus?: string | null;
}

export interface PersonaGenerateResponse {
  project_id: number;
  prompt_version: string;
  model_name: string;
  persona_count: number;
  personas: Persona[];
}
