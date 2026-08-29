"use client";

import { useState } from "react";
import { toast } from "sonner";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ExperimentForm } from "@/components/experiments/experiment-form";
import { useUpdateExperimentMutation } from "@/hooks/use-experiment";
import { getErrorMessage } from "@/components/layout/error-state";
import { ApiError, type Experiment, type Persona } from "@/types";

export function EditExperimentSheet({
  projectId,
  experiment,
  personas,
  open,
  onOpenChange,
}: {
  projectId: number;
  experiment: Experiment;
  personas: Persona[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useUpdateExperimentMutation(projectId, experiment.id);
  const [formError, setFormError] = useState<string | null>(null);
  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : [];

  const variantA = experiment.variants.find((variant) => variant.key === "A");
  const variantB = experiment.variants.find((variant) => variant.key === "B");

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) setFormError(null);
      }}
    >
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Edit experiment</SheetTitle>
          <SheetDescription>
            Only draft experiments can be edited. Changes apply before execution.
          </SheetDescription>
        </SheetHeader>
        <div className="px-4 pb-6">
          {formError ? (
            <p
              role="alert"
              className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
            >
              {formError}
            </p>
          ) : null}
          <ExperimentForm
            personas={personas}
            defaultValues={{
              name: experiment.name,
              objective: experiment.objective,
              hypothesis: experiment.hypothesis,
              scenario: experiment.scenario,
              evaluation_criteria: experiment.evaluation_criteria.map((value) => ({ value })),
              repeat_count: experiment.repeat_count,
              persona_ids: experiment.persona_ids,
              variant_a_name: variantA?.name ?? "",
              variant_a_description: variantA?.description ?? "",
              variant_b_name: variantB?.name ?? "",
              variant_b_description: variantB?.description ?? "",
            }}
            submitLabel="Save changes"
            submitting={mutation.isPending}
            fieldErrors={fieldErrors}
            onSubmit={(values) => {
              setFormError(null);
              mutation.mutate(
                {
                  name: values.name,
                  objective: values.objective,
                  hypothesis: values.hypothesis,
                  scenario: values.scenario,
                  evaluation_criteria: values.evaluation_criteria,
                  repeat_count: values.repeat_count,
                  persona_ids: values.persona_ids,
                  variants: [
                    { key: "A", name: values.variant_a_name, description: values.variant_a_description },
                    { key: "B", name: values.variant_b_name, description: values.variant_b_description },
                  ],
                },
                {
                  onSuccess: () => {
                    toast.success("Experiment updated.");
                    onOpenChange(false);
                  },
                  onError: (error) => {
                    if (error instanceof ApiError && error.fieldErrors.length === 0) {
                      setFormError(error.message);
                    } else if (!(error instanceof ApiError)) {
                      setFormError(getErrorMessage(error));
                    }
                    toast.error("Could not update experiment.");
                  },
                }
              );
            }}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}
