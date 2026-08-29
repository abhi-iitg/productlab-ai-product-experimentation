import { z } from "zod";

const requiredText = (label: string) =>
  z
    .string()
    .trim()
    .min(1, { message: `${label} is required.` });

export const projectFormSchema = z.object({
  name: requiredText("Name"),
  problem_statement: requiredText("Problem statement"),
  target_user: requiredText("Target user"),
  product_hypothesis: requiredText("Product hypothesis"),
  success_metric: requiredText("Success metric"),
  assumptions: z
    .array(z.object({ value: z.string() }))
    .transform((items) =>
      items.map((item) => item.value.trim()).filter((value) => value.length > 0)
    ),
});

export type ProjectFormValues = z.input<typeof projectFormSchema>;
export type ProjectFormOutput = z.output<typeof projectFormSchema>;
