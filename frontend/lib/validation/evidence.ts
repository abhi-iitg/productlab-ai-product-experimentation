import { z } from "zod";

export const evidenceTypeOptions = [
  { value: "interview_note", label: "Interview note" },
  { value: "survey_response", label: "Survey response" },
  { value: "support_ticket", label: "Support ticket" },
  { value: "product_review", label: "Product review" },
  { value: "research_note", label: "Research note" },
] as const;

export const evidenceFormSchema = z.object({
  evidence_type: z.enum([
    "interview_note",
    "survey_response",
    "support_ticket",
    "product_review",
    "research_note",
  ]),
  title: z.string().trim().min(1, { message: "Title is required." }),
  content: z.string().trim().min(1, { message: "Content is required." }),
  source_label: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value && value.length > 0 ? value : undefined)),
});

export type EvidenceFormValues = z.input<typeof evidenceFormSchema>;
export type EvidenceFormOutput = z.output<typeof evidenceFormSchema>;
