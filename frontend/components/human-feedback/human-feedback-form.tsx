"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import {
  useFieldArray,
  useForm,
  useWatch,
  type Control,
  type UseFormRegister,
} from "react-hook-form";

import { Button } from "@/components/ui/button";
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
  humanFeedbackFormSchema,
  scoreOptions,
  sourceMethodOptions,
  taskOutcomeOptions,
  variantKeyOptions,
  type HumanFeedbackFormOutput,
  type HumanFeedbackFormValues,
} from "@/lib/validation/human-feedback";
import type { ApiFieldError } from "@/types";

function ScoreSelector({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex gap-1.5" role="radiogroup" aria-label={label}>
        {scoreOptions.map((score) => (
          <button
            key={score}
            type="button"
            role="radio"
            aria-checked={value === score}
            onClick={() => onChange(score)}
            className={cn(
              "flex size-9 items-center justify-center rounded-md border text-sm font-medium transition-colors",
              value === score
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-background text-muted-foreground hover:text-foreground"
            )}
          >
            {score}
          </button>
        ))}
      </div>
    </div>
  );
}

type QualitativeFieldName =
  | "positive_signals"
  | "objections"
  | "confusion_points"
  | "feature_requests"
  | "uncertainty_notes";

function QualitativeListField({
  control,
  register,
  name,
  label,
  placeholder,
}: {
  control: Control<HumanFeedbackFormValues, unknown, HumanFeedbackFormOutput>;
  register: UseFormRegister<HumanFeedbackFormValues>;
  name: QualitativeFieldName;
  label: string;
  placeholder: string;
}) {
  const { fields, append, remove } = useFieldArray({ control, name });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <Button type="button" variant="ghost" size="sm" onClick={() => append({ value: "" })}>
          <Plus /> Add
        </Button>
      </div>
      {fields.length === 0 ? (
        <p className="text-xs text-muted-foreground">None recorded.</p>
      ) : (
        <div className="space-y-2">
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <Input
                aria-label={`${label} ${index + 1}`}
                placeholder={placeholder}
                {...register(`${name}.${index}.value` as const)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Remove ${label.toLowerCase()} entry`}
                onClick={() => remove(index)}
              >
                <X />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function HumanFeedbackForm({
  defaultValues,
  onSubmit,
  submitLabel,
  submitting,
  fieldErrors = [],
  formId,
}: {
  defaultValues?: Partial<HumanFeedbackFormValues>;
  onSubmit: (values: HumanFeedbackFormOutput) => void;
  submitLabel: string;
  submitting: boolean;
  fieldErrors?: ApiFieldError[];
  formId: string;
}) {
  const form = useForm<HumanFeedbackFormValues, unknown, HumanFeedbackFormOutput>({
    resolver: zodResolver(humanFeedbackFormSchema),
    defaultValues: {
      participant_label: "",
      variant_key: "A",
      source_method: "usability_test",
      session_date: "",
      task_outcome: "completed",
      clarity_score: 3,
      perceived_value_score: 3,
      adoption_intent_score: 3,
      feedback_summary: "",
      positive_signals: [],
      objections: [],
      confusion_points: [],
      feature_requests: [],
      uncertainty_notes: [],
      ...defaultValues,
    },
  });

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = form;

  const variantKey = useWatch({ control, name: "variant_key" });
  const sourceMethod = useWatch({ control, name: "source_method" });
  const taskOutcome = useWatch({ control, name: "task_outcome" });
  const clarityScore = useWatch({ control, name: "clarity_score" });
  const perceivedValueScore = useWatch({ control, name: "perceived_value_score" });
  const adoptionIntentScore = useWatch({ control, name: "adoption_intent_score" });

  const backendMessage = (field: string) =>
    fieldErrors.find((error) => error.field === field)?.message;

  return (
    <form id={formId} onSubmit={handleSubmit((values) => onSubmit(values))} className="space-y-6" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="participant_label">Participant label</Label>
          <Input
            id="participant_label"
            placeholder="e.g. Participant 1, Interview P3, Tester B-02"
            {...register("participant_label")}
            aria-invalid={!!errors.participant_label}
          />
          {(errors.participant_label?.message || backendMessage("participant_label")) && (
            <p className="text-sm text-destructive">
              {errors.participant_label?.message ?? backendMessage("participant_label")}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Use a pseudonym only — do not enter names, emails, or other identifying details.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="variant_key">Variant</Label>
          <Select
            value={variantKey}
            onValueChange={(value) =>
              setValue("variant_key", value as HumanFeedbackFormValues["variant_key"], {
                shouldValidate: true,
              })
            }
          >
            <SelectTrigger id="variant_key" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {variantKeyOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="source_method">Source method</Label>
          <Select
            value={sourceMethod}
            onValueChange={(value) =>
              setValue("source_method", value as HumanFeedbackFormValues["source_method"], {
                shouldValidate: true,
              })
            }
          >
            <SelectTrigger id="source_method" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sourceMethodOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="session_date">Session date (optional)</Label>
          <Input id="session_date" type="date" {...register("session_date")} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="task_outcome">Task outcome</Label>
          <Select
            value={taskOutcome}
            onValueChange={(value) =>
              setValue("task_outcome", value as HumanFeedbackFormValues["task_outcome"], {
                shouldValidate: true,
              })
            }
          >
            <SelectTrigger id="task_outcome" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {taskOutcomeOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <ScoreSelector
          label="Clarity (1-5)"
          value={clarityScore}
          onChange={(value) => setValue("clarity_score", value, { shouldValidate: true })}
        />
        <ScoreSelector
          label="Perceived value (1-5)"
          value={perceivedValueScore}
          onChange={(value) => setValue("perceived_value_score", value, { shouldValidate: true })}
        />
        <ScoreSelector
          label="Adoption intent (1-5)"
          value={adoptionIntentScore}
          onChange={(value) => setValue("adoption_intent_score", value, { shouldValidate: true })}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="feedback_summary">Feedback summary</Label>
        <Textarea
          id="feedback_summary"
          rows={4}
          {...register("feedback_summary")}
          aria-invalid={!!errors.feedback_summary}
        />
        {(errors.feedback_summary?.message || backendMessage("feedback_summary")) && (
          <p className="text-sm text-destructive">
            {errors.feedback_summary?.message ?? backendMessage("feedback_summary")}
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <QualitativeListField
          control={control}
          register={register}
          name="positive_signals"
          label="Positive signals"
          placeholder="e.g. Liked the guided steps"
        />
        <QualitativeListField
          control={control}
          register={register}
          name="objections"
          label="Objections"
          placeholder="e.g. Confusing pricing"
        />
        <QualitativeListField
          control={control}
          register={register}
          name="confusion_points"
          label="Confusion points"
          placeholder="e.g. Unsure what the button did"
        />
        <QualitativeListField
          control={control}
          register={register}
          name="feature_requests"
          label="Feature requests"
          placeholder="e.g. Wanted a progress indicator"
        />
        <QualitativeListField
          control={control}
          register={register}
          name="uncertainty_notes"
          label="Uncertainty notes"
          placeholder="e.g. Unclear if this generalizes"
        />
      </div>

      <Button type="submit" className="hidden" disabled={submitting}>
        {submitLabel}
      </Button>
    </form>
  );
}
