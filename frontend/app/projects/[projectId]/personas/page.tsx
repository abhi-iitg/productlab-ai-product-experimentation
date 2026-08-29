"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Sparkles, UsersRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { PageHeader } from "@/components/layout/page-header";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { PersonaCard } from "@/components/personas/persona-card";
import { PersonaGenerateDialog } from "@/components/personas/persona-generate-dialog";
import { useEvidenceQuery } from "@/hooks/use-evidence";
import { useDeletePersonaMutation, usePersonasQuery } from "@/hooks/use-personas";
import type { Persona } from "@/types";

export default function PersonasPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = Number(params.projectId);

  const { data: evidence } = useEvidenceQuery(projectId);
  const { data: personas, isPending, isError, error, refetch } = usePersonasQuery(projectId);
  const deleteMutation = useDeletePersonaMutation(projectId);

  const [generateOpen, setGenerateOpen] = useState(false);
  const [deleting, setDeleting] = useState<Persona | null>(null);

  const hasEvidence = (evidence?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personas"
        description="Evidence-grounded personas used to simulate variant responses. Personas cannot be edited manually — regenerate from evidence instead."
        actions={
          <Button onClick={() => setGenerateOpen(true)} disabled={!hasEvidence}>
            <Sparkles /> Generate personas
          </Button>
        }
      />

      {!hasEvidence && !isPending && !isError ? (
        <p className="text-sm text-muted-foreground">
          Add at least one evidence item before generating personas.
        </p>
      ) : null}

      {isPending ? (
        <SectionSkeleton rows={3} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : personas.length === 0 ? (
        <EmptyState
          icon={UsersRound}
          title="No personas yet"
          description={
            hasEvidence
              ? "Generate evidence-grounded personas to use in your experiments."
              : "Add evidence first, then generate personas grounded in that evidence."
          }
          action={
            hasEvidence ? (
              <Button onClick={() => setGenerateOpen(true)}>
                <Sparkles /> Generate personas
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-4">
          {personas.map((persona) => (
            <PersonaCard key={persona.id} persona={persona} onDelete={() => setDeleting(persona)} />
          ))}
        </div>
      )}

      <PersonaGenerateDialog
        projectId={projectId}
        evidence={evidence ?? []}
        open={generateOpen}
        onOpenChange={setGenerateOpen}
      />

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this persona?"
        description={`"${deleting?.name}" will be permanently removed. It cannot be used in new experiments after deletion.`}
        confirmLabel="Delete persona"
        destructive
        confirming={deleteMutation.isPending}
        onConfirm={() => {
          if (!deleting) return;
          deleteMutation.mutate(deleting.id, {
            onSuccess: () => {
              toast.success("Persona deleted.");
              setDeleting(null);
            },
            onError: () => toast.error("Could not delete persona."),
          });
        }}
      />
    </div>
  );
}
