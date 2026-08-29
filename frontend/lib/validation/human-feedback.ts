import { z } from "zod";

const requiredText = (label: string) =>
  z
    .string()
    .trim()
    .min(1, { message: `${label} is required.` });

const qualitativeList = z
  .array(z.object({ value: z.string() }))
  .transform((items) => items.map((item) => item.value.trim()).filter((value) => value.length > 0));

export const variantKeyOptions = [
  { value: "A", label: "Variant A" },
  { value: "B", label: "Variant B" },
] as const;

export const sourceMethodOptions = [
  { value: "interview", label: "Interview" },
  { value: "usability_test", label: "Usability test" },
  { value: "survey", label: "Survey" },
  { value: "observation", label: "Observation" },
  { value: "other", label: "Other" },
] as const;

export const taskOutcomeOptions = [
  { value: "completed", label: "Completed" },
  { value: "partially_completed", label: "Partially completed" },
  { value: "failed", label: "Failed" },
  { value: "uncertain", label: "Uncertain" },
] as const;

export const scoreOptions = [1, 2, 3, 4, 5] as const;

export const humanFeedbackFormSchema = z.object({
  participant_label: requiredText("Participant label"),
  variant_key: z.enum(["A", "B"]),
  source_method: z.enum(["interview", "usability_test", "survey", "observation", "other"]),
  session_date: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value && value.length > 0 ? value : undefined)),
  task_outcome: z.enum(["completed", "partially_completed", "failed", "uncertain"]),
  clarity_score: z.number().int().min(1).max(5),
  perceived_value_score: z.number().int().min(1).max(5),
  adoption_intent_score: z.number().int().min(1).max(5),
  feedback_summary: requiredText("Feedback summary"),
  positive_signals: qualitativeList,
  objections: qualitativeList,
  confusion_points: qualitativeList,
  feature_requests: qualitativeList,
  uncertainty_notes: qualitativeList,
});

export type HumanFeedbackFormValues = z.input<typeof humanFeedbackFormSchema>;
export type HumanFeedbackFormOutput = z.output<typeof humanFeedbackFormSchema>;
