"use client";

import { toast } from "sonner";
import { FileCheck2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState, getErrorMessage } from "@/components/layout/error-state";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { DecisionMemoView } from "@/components/decision-memo/decision-memo-view";
import { useDecisionMemoQuery, useGenerateDecisionMemoMutation } from "@/hooks/use-decision-memo";
import { useInsightsQuery } from "@/hooks/use-insights";
import { ApiError, type Experiment } from "@/types";

export function DecisionMemoTab({
  projectId,
  experiment,
}: {
  projectId: number;
  experiment: Experiment;
}) {
  const { data: memo, isPending, isError, error, refetch } = useDecisionMemoQuery(
    projectId,
    experiment.id
  );
  const { data: insights } = useInsightsQuery(projectId, experiment.id);
  const generateMutation = useGenerateDecisionMemoMutation(projectId, experiment.id);

  if (isPending) return <SectionSkeleton rows={3} />;

  if (isError) {
    if (!(error instanceof ApiError) || error.kind !== "not_found") {
      return <ErrorState error={error} onRetry={() => refetch()} />;
    }
  } else if (memo) {
    return <DecisionMemoView memo={memo} />;
  }

  const hasInsights = (insights?.length ?? 0) > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-2 pt-6 text-sm text-foreground">
          <p className="font-medium">What the recommendation means</p>
          <ul className="list-inside list-disc space-y-1 text-muted-foreground">
            <li>
              <span className="font-medium text-foreground">Proceed to real-user validation</span>{" "}
              — synthetic results support moving to real-user testing, not launch.
            </li>
            <li>
              <span className="font-medium text-foreground">Iterate before validation</span> — the
              concept needs changes before it is worth testing with real users.
            </li>
            <li>
              <span className="font-medium text-foreground">
                Stop investment in the current concept
              </span>{" "}
              — synthetic signals do not support continued investment as-is.
            </li>
          </ul>
        </CardContent>
      </Card>

      <EmptyState
        icon={FileCheck2}
        title="No decision memo yet"
        description={
          hasInsights
            ? "Generate a Proceed / Iterate / Stop recommendation grounded in this experiment's insights and analytics."
            : "Generate insights first — a decision memo requires at least one insight."
        }
        action={
          hasInsights ? (
            <Button
              onClick={() => {
                generateMutation.mutate(undefined, {
                  onSuccess: () => toast.success("Decision memo generated."),
                  onError: () => toast.error("Could not generate decision memo."),
                });
              }}
              disabled={generateMutation.isPending}
            >
              <Sparkles /> {generateMutation.isPending ? "Generating…" : "Generate decision memo"}
            </Button>
          ) : undefined
        }
      />

      {generateMutation.isError ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
        >
          {getErrorMessage(generateMutation.error)}
        </p>
      ) : null}
    </div>
  );
}
