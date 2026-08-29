"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { ResponsibleAiNotice } from "@/components/layout/responsible-ai-notice";
import { ExperimentForm } from "@/components/experiments/experiment-form";
import { usePersonasQuery } from "@/hooks/use-personas";
import { useCreateExperimentMutation } from "@/hooks/use-experiments";
import { getErrorMessage } from "@/components/layout/error-state";
import { ApiError, type ExperimentCreateInput } from "@/types";

export default function NewExperimentPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = Number(params.projectId);
  const router = useRouter();

  const { data: personas } = usePersonasQuery(projectId);
  const mutation = useCreateExperimentMutation(projectId);
  const [formError, setFormError] = useState<string | null>(null);

  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : [];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="New experiment"
        description="Configure a two-variant A/B experiment. Both variants run against the same personas and scenario."
      />
      <ResponsibleAiNotice />

      {formError ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
        >
          {formError}
        </p>
      ) : null}

      <ExperimentForm
        personas={personas ?? []}
        submitLabel="Create experiment"
        submitting={mutation.isPending}
        fieldErrors={fieldErrors}
        onSubmit={(values) => {
          setFormError(null);
          const input: ExperimentCreateInput = {
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
          };
          mutation.mutate(input, {
            onSuccess: (experiment) => {
              toast.success("Experiment created.");
              router.push(`/projects/${projectId}/experiments/${experiment.id}`);
            },
            onError: (error) => {
              if (error instanceof ApiError && error.fieldErrors.length === 0) {
                setFormError(error.message);
              } else if (!(error instanceof ApiError)) {
                setFormError(getErrorMessage(error));
              }
              toast.error("Could not create experiment.");
            },
          });
        }}
      />
    </div>
  );
}
