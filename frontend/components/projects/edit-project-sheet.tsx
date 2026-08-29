"use client";

import { useState } from "react";
import { toast } from "sonner";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { ProjectForm } from "@/components/projects/project-form";
import { useUpdateProjectMutation } from "@/hooks/use-project";
import { getErrorMessage } from "@/components/layout/error-state";
import { ApiError, type Project } from "@/types";

export function EditProjectSheet({
  project,
  open,
  onOpenChange,
}: {
  project: Project;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useUpdateProjectMutation(project.id);
  const [formError, setFormError] = useState<string | null>(null);
  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : [];

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) setFormError(null);
      }}
    >
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Edit project</SheetTitle>
          <SheetDescription>Update the product brief for {project.name}.</SheetDescription>
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
          <ProjectForm
            defaultValues={{
              name: project.name,
              problem_statement: project.problem_statement,
              target_user: project.target_user,
              product_hypothesis: project.product_hypothesis,
              success_metric: project.success_metric,
              assumptions:
                project.assumptions.length > 0
                  ? project.assumptions.map((value) => ({ value }))
                  : [{ value: "" }],
            }}
            submitLabel="Save changes"
            submitting={mutation.isPending}
            fieldErrors={fieldErrors}
            onSubmit={(values) => {
              setFormError(null);
              mutation.mutate(values, {
                onSuccess: () => {
                  toast.success("Project updated.");
                  onOpenChange(false);
                },
                onError: (error) => {
                  if (error instanceof ApiError && error.fieldErrors.length === 0) {
                    setFormError(error.message);
                  } else if (!(error instanceof ApiError)) {
                    setFormError(getErrorMessage(error));
                  }
                  toast.error("Could not update project.");
                },
              });
            }}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}
