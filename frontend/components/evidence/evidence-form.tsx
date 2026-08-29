"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";

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
import { evidenceFormSchema, evidenceTypeOptions, type EvidenceFormOutput, type EvidenceFormValues } from "@/lib/validation/evidence";
import type { ApiFieldError } from "@/types";

export function EvidenceForm({
  defaultValues,
  onSubmit,
  submitLabel,
  submitting,
  fieldErrors = [],
  formId,
}: {
  defaultValues?: Partial<EvidenceFormValues>;
  onSubmit: (values: EvidenceFormOutput) => void;
  submitLabel: string;
  submitting: boolean;
  fieldErrors?: ApiFieldError[];
  formId: string;
}) {
  const form = useForm<EvidenceFormValues, unknown, EvidenceFormOutput>({
    resolver: zodResolver(evidenceFormSchema),
    defaultValues: {
      evidence_type: "interview_note",
      title: "",
      content: "",
      source_label: "",
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

  const evidenceType = useWatch({ control, name: "evidence_type" });

  const backendMessage = (field: string) =>
    fieldErrors.find((error) => error.field === field)?.message;

  return (
    <form id={formId} onSubmit={handleSubmit((values) => onSubmit(values))} className="space-y-4" noValidate>
      <div className="space-y-2">
        <Label htmlFor="evidence_type">Evidence type</Label>
        <Select
          value={evidenceType}
          onValueChange={(value) => setValue("evidence_type", value as EvidenceFormValues["evidence_type"], { shouldValidate: true })}
        >
          <SelectTrigger id="evidence_type" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {evidenceTypeOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input id="title" {...register("title")} aria-invalid={!!errors.title} />
        {(errors.title?.message || backendMessage("title")) && (
          <p className="text-sm text-destructive">{errors.title?.message ?? backendMessage("title")}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">Content</Label>
        <Textarea
          id="content"
          rows={8}
          {...register("content")}
          aria-invalid={!!errors.content}
        />
        {(errors.content?.message || backendMessage("content")) && (
          <p className="text-sm text-destructive">{errors.content?.message ?? backendMessage("content")}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="source_label">Source label (optional)</Label>
        <Input
          id="source_label"
          placeholder="e.g. Interview #4, NPS survey batch 2"
          {...register("source_label")}
        />
      </div>

      <Button type="submit" className="hidden" disabled={submitting}>
        {submitLabel}
      </Button>
    </form>
  );
}
