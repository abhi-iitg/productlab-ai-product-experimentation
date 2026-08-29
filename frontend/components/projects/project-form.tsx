"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import { useForm, useFieldArray } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { projectFormSchema, type ProjectFormOutput, type ProjectFormValues } from "@/lib/validation/project";
import type { ApiFieldError } from "@/types";

export function ProjectForm({
  defaultValues,
  onSubmit,
  submitLabel,
  submitting,
  fieldErrors = [],
}: {
  defaultValues?: Partial<ProjectFormValues>;
  onSubmit: (values: ProjectFormOutput) => void;
  submitLabel: string;
  submitting: boolean;
  fieldErrors?: ApiFieldError[];
}) {
  const form = useForm<ProjectFormValues, unknown, ProjectFormOutput>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      name: "",
      problem_statement: "",
      target_user: "",
      product_hypothesis: "",
      success_metric: "",
      assumptions: [{ value: "" }],
      ...defaultValues,
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "assumptions",
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = form;

  const backendMessage = (field: string) =>
    fieldErrors.find((error) => error.field === field)?.message;

  return (
    <form
      onSubmit={handleSubmit((values) => onSubmit(values))}
      className="space-y-6"
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input id="name" autoComplete="off" {...register("name")} aria-invalid={!!errors.name} />
        {(errors.name?.message || backendMessage("name")) && (
          <p className="text-sm text-destructive">{errors.name?.message ?? backendMessage("name")}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="problem_statement">Problem statement</Label>
        <Textarea
          id="problem_statement"
          rows={3}
          {...register("problem_statement")}
          aria-invalid={!!errors.problem_statement}
        />
        {(errors.problem_statement?.message || backendMessage("problem_statement")) && (
          <p className="text-sm text-destructive">
            {errors.problem_statement?.message ?? backendMessage("problem_statement")}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="target_user">Target user</Label>
        <Textarea
          id="target_user"
          rows={2}
          {...register("target_user")}
          aria-invalid={!!errors.target_user}
        />
        {(errors.target_user?.message || backendMessage("target_user")) && (
          <p className="text-sm text-destructive">
            {errors.target_user?.message ?? backendMessage("target_user")}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="product_hypothesis">Product hypothesis</Label>
        <Textarea
          id="product_hypothesis"
          rows={3}
          {...register("product_hypothesis")}
          aria-invalid={!!errors.product_hypothesis}
        />
        {(errors.product_hypothesis?.message || backendMessage("product_hypothesis")) && (
          <p className="text-sm text-destructive">
            {errors.product_hypothesis?.message ?? backendMessage("product_hypothesis")}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="success_metric">Success metric</Label>
        <Input
          id="success_metric"
          {...register("success_metric")}
          aria-invalid={!!errors.success_metric}
        />
        {(errors.success_metric?.message || backendMessage("success_metric")) && (
          <p className="text-sm text-destructive">
            {errors.success_metric?.message ?? backendMessage("success_metric")}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Assumptions</Label>
          <Button type="button" variant="ghost" size="sm" onClick={() => append({ value: "" })}>
            <Plus /> Add assumption
          </Button>
        </div>
        <div className="space-y-2">
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <Input
                aria-label={`Assumption ${index + 1}`}
                {...register(`assumptions.${index}.value` as const)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Remove assumption"
                onClick={() => remove(index)}
                disabled={fields.length === 1}
              >
                <X />
              </Button>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Blank assumptions are ignored automatically.
        </p>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
