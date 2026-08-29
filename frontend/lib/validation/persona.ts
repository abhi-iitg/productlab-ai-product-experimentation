import { z } from "zod";

export const personaGenerateFormSchema = z
  .object({
    persona_count: z.number().int().min(2).max(5),
    evidence_scope: z.enum(["all", "selected"]),
    selected_evidence_ids: z.array(z.number()),
    focus: z.string().trim().optional(),
  })
  .refine(
    (values) => values.evidence_scope === "all" || values.selected_evidence_ids.length > 0,
    { message: "Select at least one evidence item.", path: ["selected_evidence_ids"] }
  );

export type PersonaGenerateFormValues = z.input<typeof personaGenerateFormSchema>;
