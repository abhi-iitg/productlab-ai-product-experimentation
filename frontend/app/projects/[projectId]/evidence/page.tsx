"use client";

import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { FileText, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { PageHeader } from "@/components/layout/page-header";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { EvidenceDetailDialog } from "@/components/evidence/evidence-detail-dialog";
import { EvidenceItemDialog } from "@/components/evidence/evidence-item-dialog";
import { useDeleteEvidenceMutation, useEvidenceQuery } from "@/hooks/use-evidence";
import { evidenceTypeOptions } from "@/lib/validation/evidence";
import { cn } from "@/lib/utils";
import type { EvidenceItem, EvidenceType } from "@/types";

export default function EvidencePage() {
  const params = useParams<{ projectId: string }>();
  const projectId = Number(params.projectId);

  const { data: evidence, isPending, isError, error, refetch } = useEvidenceQuery(projectId);
  const deleteMutation = useDeleteEvidenceMutation(projectId);

  const [typeFilter, setTypeFilter] = useState<EvidenceType | "all">("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<EvidenceItem | null>(null);
  const [viewing, setViewing] = useState<EvidenceItem | null>(null);
  const [deleting, setDeleting] = useState<EvidenceItem | null>(null);

  const filtered = useMemo(() => {
    if (!evidence) return [];
    if (typeFilter === "all") return evidence;
    return evidence.filter((item) => item.evidence_type === typeFilter);
  }, [evidence, typeFilter]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence"
        description="Text-based research your personas will be grounded in. Persona quality depends directly on the evidence you add here."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> Add evidence
          </Button>
        }
      />

      {isPending ? (
        <SectionSkeleton rows={4} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : evidence.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No evidence yet"
          description="Add interview notes, survey responses, support tickets, product reviews, or research notes. Personas cannot be generated without at least one evidence item."
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus /> Add your first evidence item
            </Button>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by evidence type">
            <button
              type="button"
              onClick={() => setTypeFilter("all")}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                typeFilter === "all"
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-muted-foreground hover:text-foreground"
              )}
            >
              All ({evidence.length})
            </button>
            {evidenceTypeOptions.map((option) => {
              const count = evidence.filter((item) => item.evidence_type === option.value).length;
              if (count === 0) return null;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setTypeFilter(option.value)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    typeFilter === option.value
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-background text-muted-foreground hover:text-foreground"
                  )}
                >
                  {option.label} ({count})
                </button>
              );
            })}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((item) => (
              <EvidenceCard
                key={item.id}
                evidence={item}
                onView={() => setViewing(item)}
                onEdit={() => setEditing(item)}
                onDelete={() => setDeleting(item)}
              />
            ))}
          </div>
        </>
      )}

      <EvidenceItemDialog projectId={projectId} open={createOpen} onOpenChange={setCreateOpen} />
      <EvidenceItemDialog
        projectId={projectId}
        open={!!editing}
        onOpenChange={(open) => !open && setEditing(null)}
        evidence={editing}
      />
      <EvidenceDetailDialog
        evidence={viewing}
        open={!!viewing}
        onOpenChange={(open) => !open && setViewing(null)}
      />
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this evidence item?"
        description={`"${deleting?.title}" will be permanently removed. Personas already generated will keep their existing citations.`}
        confirmLabel="Delete evidence"
        destructive
        confirming={deleteMutation.isPending}
        onConfirm={() => {
          if (!deleting) return;
          deleteMutation.mutate(deleting.id, {
            onSuccess: () => {
              toast.success("Evidence deleted.");
              setDeleting(null);
            },
            onError: () => toast.error("Could not delete evidence."),
          });
        }}
      />
    </div>
  );
}
