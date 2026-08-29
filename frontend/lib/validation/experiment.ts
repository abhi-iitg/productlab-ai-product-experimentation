import { z } from "zod";

import { MAX_SIMULATION_RUNS } from "@/types";

const requiredText = (label: string) =>
  z
    .string()
    .trim()
    .min(1, { message: `${label} is required.` });

const criteriaList = z
  .array(z.object({ value: z.string() }))
  .transform((items) => items.map((item) => item.value.trim()).filter((value) => value.length > 0))
  .refine((values) => values.length > 0, {
    message: "At least one evaluation criterion is required.",
  });

export const experimentFormSchema = z
  .object({
    name: requiredText("Name"),
    objective: requiredText("Objective"),
    hypothesis: requiredText("Hypothesis"),
    scenario: requiredText("Shared scenario"),
    evaluation_criteria: criteriaList,
    repeat_count: z.number().int().min(1).max(3),
    persona_ids: z.array(z.number()).min(1, { message: "Select at least one persona." }),
    variant_a_name: requiredText("Variant A name"),
    variant_a_description: requiredText("Variant A description"),
    variant_b_name: requiredText("Variant B name"),
    variant_b_description: requiredText("Variant B description"),
  })
  .refine(
    (values) => values.persona_ids.length * 2 * values.repeat_count <= MAX_SIMULATION_RUNS,
    {
      message: `Planned runs exceed the maximum of ${MAX_SIMULATION_RUNS}. Reduce personas or repeat count.`,
      path: ["persona_ids"],
    }
  );

export type ExperimentFormValues = z.input<typeof experimentFormSchema>;
export type ExperimentFormOutput = z.output<typeof experimentFormSchema>;
