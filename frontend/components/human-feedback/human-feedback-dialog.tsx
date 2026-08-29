"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { HumanFeedbackForm } from "@/components/human-feedback/human-feedback-form";
import {
  useCreateHumanFeedbackMutation,
  useUpdateHumanFeedbackMutation,
} from "@/hooks/use-human-feedback";
import { ApiError, type HumanFeedback } from "@/types";
import type { HumanFeedbackFormValues } from "@/lib/validation/human-feedback";

const FORM_ID = "human-feedback-form";

export function HumanFeedbackDialog({
  projectId,
  experimentId,
  open,
  onOpenChange,
  feedback,
}: {
  projectId: number;
  experimentId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  feedback?: HumanFeedback | null;
}) {
  const isEditing = !!feedback;
  const createMutation = useCreateHumanFeedbackMutation(projectId, experimentId);
  const updateMutation = useUpdateHumanFeedbackMutation(projectId, experimentId);
  const mutation = isEditing ? updateMutation : createMutation;
  const [formError, setFormError] = useState<string | null>(null);

  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : [];

  const defaultValues: Partial<HumanFeedbackFormValues> | undefined = feedback
    ? {
        participant_label: feedback.participant_label,
        variant_key: feedback.variant_key,
        source_method: feedback.source_method,
        session_date: feedback.session_date ?? "",
        task_outcome: feedback.task_outcome,
        clarity_score: feedback.clarity_score,
        perceived_value_score: feedback.perceived_value_score,
        adoption_intent_score: feedback.adoption_intent_score,
        feedback_summary: feedback.feedback_summary,
        positive_signals: feedback.positive_signals.map((value) => ({ value })),
        objections: feedback.objections.map((value) => ({ value })),
        confusion_points: feedback.confusion_points.map((value) => ({ value })),
        feature_requests: feedback.feature_requests.map((value) => ({ value })),
        uncertainty_notes: feedback.uncertainty_notes.map((value) => ({ value })),
      }
    : undefined;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) setFormError(null);
      }}
    >
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit real feedback" : "Add real feedback"}</DialogTitle>
          <DialogDescription>
            Enter anonymized feedback only. Do not include names, emails, or other identifying
            information — use a pseudonymous label instead.
          </DialogDescription>
        </DialogHeader>

        {formError ? (
          <p
            role="alert"
            className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {formError}
          </p>
        ) : null}

        <HumanFeedbackForm
          formId={FORM_ID}
          defaultValues={defaultValues}
          submitLabel={isEditing ? "Save changes" : "Add feedback"}
          submitting={mutation.isPending}
          fieldErrors={fieldErrors}
          onSubmit={(values) => {
            setFormError(null);
            const handlers = {
              onSuccess: () => {
                toast.success(isEditing ? "Feedback updated." : "Feedback added.");
                onOpenChange(false);
              },
              onError: (error: unknown) => {
                if (error instanceof ApiError && error.fieldErrors.length === 0) {
                  setFormError(error.message);
                } else if (!(error instanceof ApiError)) {
                  setFormError("Something went wrong. Please try again.");
                }
                toast.error(isEditing ? "Could not update feedback." : "Could not add feedback.");
              },
            };
            if (isEditing && feedback) {
              updateMutation.mutate({ feedbackId: feedback.id, input: values }, handlers);
            } else {
              createMutation.mutate(values, handlers);
            }
          }}
        />

        <DialogFooter>
          <Button type="submit" form={FORM_ID} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : isEditing ? "Save changes" : "Add feedback"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
