export type EvidenceType =
  | "interview_note"
  | "survey_response"
  | "support_ticket"
  | "product_review"
  | "research_note";

export interface EvidenceItem {
  id: number;
  project_id: number;
  evidence_type: EvidenceType;
  title: string;
  content: string;
  source_label: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvidenceItemCreateInput {
  evidence_type: EvidenceType;
  title: string;
  content: string;
  source_label?: string | null;
}

export interface EvidenceItemUpdateInput {
  evidence_type?: EvidenceType;
  title?: string;
  content?: string;
  source_label?: string | null;
}
