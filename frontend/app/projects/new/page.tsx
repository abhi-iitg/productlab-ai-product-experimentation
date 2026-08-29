"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/layout/page-header";
import { ProjectForm } from "@/components/projects/project-form";
import { useCreateProjectMutation } from "@/hooks/use-projects";
import { getErrorMessage } from "@/components/layout/error-state";
import { ApiError, type ProjectCreateInput } from "@/types";

export default function NewProjectPage() {
  const router = useRouter();
  const mutation = useCreateProjectMutation();
  const [formError, setFormError] = useState<string | null>(null);

  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : [];

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8 sm:px-6">
      <PageHeader
        title="New project"
        description="Create the product brief that grounds evidence, personas, and experiments for this concept."
      />

      <Card>
        <CardContent className="pt-6">
          {formError ? (
            <p role="alert" className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {formError}
            </p>
          ) : null}
          <ProjectForm
            submitLabel="Create project"
            submitting={mutation.isPending}
            fieldErrors={fieldErrors}
            onSubmit={(values) => {
              setFormError(null);
              const input: ProjectCreateInput = {
                ...values,
              };
              mutation.mutate(input, {
                onSuccess: (project) => {
                  toast.success("Project created.");
                  router.push(`/projects/${project.id}`);
                },
                onError: (error) => {
                  if (error instanceof ApiError && error.fieldErrors.length === 0) {
                    setFormError(error.message);
                  } else if (!(error instanceof ApiError)) {
                    setFormError(getErrorMessage(error));
                  }
                  toast.error("Could not create project.");
                },
              });
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
