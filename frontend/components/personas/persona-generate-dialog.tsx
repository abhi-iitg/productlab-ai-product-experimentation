"use client";

import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PersonaGenerateForm } from "@/components/personas/persona-generate-form";
import { useGeneratePersonasMutation } from "@/hooks/use-personas";
import { getErrorMessage } from "@/components/layout/error-state";
import type { EvidenceItem } from "@/types";

export function PersonaGenerateDialog({
  projectId,
  evidence,
  open,
  onOpenChange,
}: {
  projectId: number;
  evidence: EvidenceItem[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useGeneratePersonasMutation(projectId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Generate personas</DialogTitle>
          <DialogDescription>
            Personas are generated from your evidence library and grounded with explicit
            citations. This can take up to a minute.
          </DialogDescription>
        </DialogHeader>

        {mutation.isPending ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Generating personas from evidence — this may take a moment…
            </p>
          </div>
        ) : (
          <>
            {mutation.isError ? (
              <p
                role="alert"
                className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              >
                {getErrorMessage(mutation.error)}
              </p>
            ) : null}
            <PersonaGenerateForm
              evidence={evidence}
              submitting={mutation.isPending}
              onSubmit={(input) => {
                mutation.mutate(input, {
                  onSuccess: (response) => {
                    toast.success(`Generated ${response.persona_count} personas.`);
                    onOpenChange(false);
                  },
                  onError: () => {
                    toast.error("Could not generate personas.");
                  },
                });
              }}
            />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
