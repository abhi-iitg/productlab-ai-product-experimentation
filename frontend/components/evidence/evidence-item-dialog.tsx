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
import { EvidenceForm } from "@/components/evidence/evidence-form";
import { useCreateEvidenceMutation, useUpdateEvidenceMutation } from "@/hooks/use-evidence";
import { ApiError, type EvidenceItem } from "@/types";
import type { EvidenceFormValues } from "@/lib/validation/evidence";

const FORM_ID = "evidence-item-form";

export function EvidenceItemDialog({
  projectId,
  open,
  onOpenChange,
  evidence,
}: {
  projectId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  evidence?: EvidenceItem | null;
}) {
  const isEditing = !!evidence;
  const createMutation = useCreateEvidenceMutation(projectId);
  const updateMutation = useUpdateEvidenceMutation(projectId);
  const mutation = isEditing ? updateMutation : createMutation;
  const [formError, setFormError] = useState<string | null>(null);

  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : [];

  const defaultValues: Partial<EvidenceFormValues> | undefined = evidence
    ? {
        evidence_type: evidence.evidence_type,
        title: evidence.title,
        content: evidence.content,
        source_label: evidence.source_label ?? "",
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
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit evidence" : "Add evidence"}</DialogTitle>
          <DialogDescription>
            Text evidence only. Persona quality depends directly on the evidence you provide here.
          </DialogDescription>
        </DialogHeader>

        {formError ? (
          <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <EvidenceForm
          formId={FORM_ID}
          defaultValues={defaultValues}
          submitLabel={isEditing ? "Save changes" : "Add evidence"}
          submitting={mutation.isPending}
          fieldErrors={fieldErrors}
          onSubmit={(values) => {
            setFormError(null);
            const handlers = {
              onSuccess: () => {
                toast.success(isEditing ? "Evidence updated." : "Evidence added.");
                onOpenChange(false);
              },
              onError: (error: unknown) => {
                if (error instanceof ApiError && error.fieldErrors.length === 0) {
                  setFormError(error.message);
                } else if (!(error instanceof ApiError)) {
                  setFormError("Something went wrong. Please try again.");
                }
                toast.error(isEditing ? "Could not update evidence." : "Could not add evidence.");
              },
            };
            if (isEditing && evidence) {
              updateMutation.mutate({ evidenceId: evidence.id, input: values }, handlers);
            } else {
              createMutation.mutate(values, handlers);
            }
          }}
        />

        <DialogFooter>
          <Button type="submit" form={FORM_ID} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : isEditing ? "Save changes" : "Add evidence"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
