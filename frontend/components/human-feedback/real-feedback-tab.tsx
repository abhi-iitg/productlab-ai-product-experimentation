"use client";

import { useState } from "react";
import { toast } from "sonner";
import { MessagesSquare, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { HumanFeedbackCard } from "@/components/human-feedback/human-feedback-card";
import { HumanFeedbackDialog } from "@/components/human-feedback/human-feedback-dialog";
import { HumanComparisonView } from "@/components/human-feedback/human-comparison-view";
import { PrivacyNotice, QualitativeSampleNotice } from "@/components/human-feedback/notices";
import {
  useDeleteHumanFeedbackMutation,
  useHumanComparisonQuery,
  useHumanFeedbackQuery,
} from "@/hooks/use-human-feedback";
import { ApiError, type Experiment, type HumanFeedback } from "@/types";

const INELIGIBLE_MESSAGE =
  "Human feedback can only be added once this experiment is completed or partially completed.";

export function RealFeedbackTab({
  projectId,
  experiment,
}: {
  projectId: number;
  experiment: Experiment;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<HumanFeedback | null>(null);
  const [deleting, setDeleting] = useState<HumanFeedback | null>(null);

  const {
    data: feedback,
    isPending,
    isError,
    error,
    refetch,
  } = useHumanFeedbackQuery(projectId, experiment.id);
  const comparisonQuery = useHumanComparisonQuery(projectId, experiment.id);
  const deleteMutation = useDeleteHumanFeedbackMutation(projectId, experiment.id);

  const eligible = experiment.status === "completed" || experiment.status === "partially_completed";

  if (isPending) return <SectionSkeleton rows={3} />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <PrivacyNotice />
        <QualitativeSampleNotice />
      </div>

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">Participant feedback</h3>
        <Button onClick={() => setCreateOpen(true)} disabled={!eligible} title={!eligible ? INELIGIBLE_MESSAGE : undefined}>
          <Plus /> Add feedback
        </Button>
      </div>
      {!eligible ? <p className="text-xs text-muted-foreground">{INELIGIBLE_MESSAGE}</p> : null}

      {feedback.length === 0 ? (
        <EmptyState
          icon={MessagesSquare}
          title="No real feedback yet"
          description={
            eligible
              ? "Add anonymized feedback collected from real participants to compare it against the synthetic findings."
              : INELIGIBLE_MESSAGE
          }
          action={
            eligible ? (
              <Button onClick={() => setCreateOpen(true)}>
                <Plus /> Add feedback
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-4">
          {feedback.map((item) => (
            <HumanFeedbackCard
              key={item.id}
              feedback={item}
              onEdit={() => setEditing(item)}
              onDelete={() => setDeleting(item)}
            />
          ))}
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-medium text-foreground">Real vs. synthetic comparison</h3>
        {comparisonQuery.isPending ? (
          <SectionSkeleton rows={2} />
        ) : comparisonQuery.isError ? (
          comparisonQuery.error instanceof ApiError && comparisonQuery.error.kind === "conflict" ? (
            <EmptyState
              icon={MessagesSquare}
              title="Comparison not available yet"
              description={comparisonQuery.error.message}
            />
          ) : (
            <ErrorState error={comparisonQuery.error} onRetry={() => comparisonQuery.refetch()} />
          )
        ) : (
          <HumanComparisonView comparison={comparisonQuery.data} />
        )}
      </div>

      <HumanFeedbackDialog
        projectId={projectId}
        experimentId={experiment.id}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
      <HumanFeedbackDialog
        projectId={projectId}
        experimentId={experiment.id}
        open={!!editing}
        onOpenChange={(open) => !open && setEditing(null)}
        feedback={editing}
      />
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this feedback?"
        description={`Feedback from "${deleting?.participant_label}" will be permanently removed. This cannot be undone.`}
        confirmLabel="Delete feedback"
        destructive
        confirming={deleteMutation.isPending}
        onConfirm={() => {
          if (!deleting) return;
          deleteMutation.mutate(deleting.id, {
            onSuccess: () => {
              toast.success("Feedback deleted.");
              setDeleting(null);
            },
            onError: () => toast.error("Could not delete feedback."),
          });
        }}
      />
    </div>
  );
}
