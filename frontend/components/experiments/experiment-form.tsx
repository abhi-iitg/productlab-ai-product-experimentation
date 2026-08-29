"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import { useForm, useFieldArray, useWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  experimentFormSchema,
  type ExperimentFormOutput,
  type ExperimentFormValues,
} from "@/lib/validation/experiment";
import { MAX_SIMULATION_RUNS, type ApiFieldError, type Persona } from "@/types";

export function ExperimentForm({
  personas,
  defaultValues,
  onSubmit,
  submitLabel,
  submitting,
  fieldErrors = [],
}: {
  personas: Persona[];
  defaultValues?: Partial<ExperimentFormValues>;
  onSubmit: (values: ExperimentFormOutput) => void;
  submitLabel: string;
  submitting: boolean;
  fieldErrors?: ApiFieldError[];
}) {
  const form = useForm<ExperimentFormValues, unknown, ExperimentFormOutput>({
    resolver: zodResolver(experimentFormSchema),
    defaultValues: {
      name: "",
      objective: "",
      hypothesis: "",
      scenario: "",
      evaluation_criteria: [{ value: "" }],
      repeat_count: 1,
      persona_ids: [],
      variant_a_name: "",
      variant_a_description: "",
      variant_b_name: "",
      variant_b_description: "",
      ...defaultValues,
    },
  });

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors },
  } = form;

  const { fields, append, remove } = useFieldArray({
    control,
    name: "evaluation_criteria",
  });

  const personaIds = useWatch({ control, name: "persona_ids" });
  const repeatCount = useWatch({ control, name: "repeat_count" });
  const plannedRuns = personaIds.length * 2 * repeatCount;
  const overLimit = plannedRuns > MAX_SIMULATION_RUNS;

  const backendMessage = (field: string) =>
    fieldErrors.find((error) => error.field === field)?.message;

  return (
    <form onSubmit={handleSubmit((values) => onSubmit(values))} className="space-y-8" noValidate>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Experiment details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} aria-invalid={!!errors.name} />
            {(errors.name?.message || backendMessage("name")) && (
              <p className="text-sm text-destructive">{errors.name?.message ?? backendMessage("name")}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="objective">Objective</Label>
            <Textarea id="objective" rows={2} {...register("objective")} aria-invalid={!!errors.objective} />
            {(errors.objective?.message || backendMessage("objective")) && (
              <p className="text-sm text-destructive">
                {errors.objective?.message ?? backendMessage("objective")}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="hypothesis">Hypothesis</Label>
            <Textarea id="hypothesis" rows={2} {...register("hypothesis")} aria-invalid={!!errors.hypothesis} />
            {(errors.hypothesis?.message || backendMessage("hypothesis")) && (
              <p className="text-sm text-destructive">
                {errors.hypothesis?.message ?? backendMessage("hypothesis")}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="scenario">Shared scenario</Label>
            <Textarea id="scenario" rows={3} {...register("scenario")} aria-invalid={!!errors.scenario} />
            <p className="text-xs text-muted-foreground">
              Both variants simulate this same scenario against the same personas — only the
              variant description differs.
            </p>
            {(errors.scenario?.message || backendMessage("scenario")) && (
              <p className="text-sm text-destructive">
                {errors.scenario?.message ?? backendMessage("scenario")}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Evaluation criteria</Label>
              <Button type="button" variant="ghost" size="sm" onClick={() => append({ value: "" })}>
                <Plus /> Add criterion
              </Button>
            </div>
            <div className="space-y-2">
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-2">
                  <Input
                    aria-label={`Evaluation criterion ${index + 1}`}
                    {...register(`evaluation_criteria.${index}.value` as const)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Remove criterion"
                    onClick={() => remove(index)}
                    disabled={fields.length === 1}
                  >
                    <X />
                  </Button>
                </div>
              ))}
            </div>
            {errors.evaluation_criteria?.message ? (
              <p className="text-sm text-destructive">{errors.evaluation_criteria.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="repeat_count">Repeat count</Label>
            <Select
              value={String(repeatCount)}
              onValueChange={(value) => setValue("repeat_count", Number(value), { shouldValidate: true })}
            >
              <SelectTrigger id="repeat_count" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3].map((count) => (
                  <SelectItem key={count} value={String(count)}>
                    {count}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              How many times each persona runs each variant.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {personas.length === 0 ? (
            <p className="text-sm text-muted-foreground">No personas available.</p>
          ) : (
            <div className="space-y-1">
              {personas.map((persona) => {
                const checked = personaIds.includes(persona.id);
                return (
                  <label
                    key={persona.id}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-md p-2 text-sm hover:bg-muted",
                      checked && "bg-muted"
                    )}
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) => {
                        const next = value
                          ? [...personaIds, persona.id]
                          : personaIds.filter((id) => id !== persona.id);
                        setValue("persona_ids", next, { shouldValidate: true });
                      }}
                    />
                    <span className="font-medium text-foreground">{persona.name}</span>
                    <span className="text-xs text-muted-foreground">{persona.segment_label}</span>
                  </label>
                );
              })}
            </div>
          )}
          {errors.persona_ids?.message ? (
            <p className="text-sm text-destructive">{errors.persona_ids.message}</p>
          ) : null}
        </CardContent>
      </Card>

      <div
        className={cn(
          "rounded-lg border px-4 py-3 text-sm",
          overLimit
            ? "border-destructive/40 bg-destructive/5 text-destructive"
            : "border-border bg-muted/50 text-foreground"
        )}
        role="status"
      >
        Planned runs: <span className="font-semibold">{plannedRuns}</span> ({personaIds.length}{" "}
        personas × 2 variants × {repeatCount} repeats). Maximum allowed is{" "}
        {MAX_SIMULATION_RUNS}.
        {overLimit ? " Reduce personas or the repeat count to continue." : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Variant A</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="variant_a_name">Name</Label>
              <Input id="variant_a_name" {...register("variant_a_name")} aria-invalid={!!errors.variant_a_name} />
              {(errors.variant_a_name?.message || backendMessage("variant_a_name")) && (
                <p className="text-sm text-destructive">{errors.variant_a_name?.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="variant_a_description">Description</Label>
              <Textarea
                id="variant_a_description"
                rows={4}
                {...register("variant_a_description")}
                aria-invalid={!!errors.variant_a_description}
              />
              {errors.variant_a_description?.message ? (
                <p className="text-sm text-destructive">{errors.variant_a_description.message}</p>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Variant B</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="variant_b_name">Name</Label>
              <Input id="variant_b_name" {...register("variant_b_name")} aria-invalid={!!errors.variant_b_name} />
              {errors.variant_b_name?.message ? (
                <p className="text-sm text-destructive">{errors.variant_b_name.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="variant_b_description">Description</Label>
              <Textarea
                id="variant_b_description"
                rows={4}
                {...register("variant_b_description")}
                aria-invalid={!!errors.variant_b_description}
              />
              {errors.variant_b_description?.message ? (
                <p className="text-sm text-destructive">{errors.variant_b_description.message}</p>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="submit" disabled={submitting || overLimit}>
          {submitting ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
