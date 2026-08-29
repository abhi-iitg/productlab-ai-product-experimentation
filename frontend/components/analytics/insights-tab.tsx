"use client";

import { toast } from "sonner";
import { Lightbulb, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { InsightCard } from "@/components/analytics/insight-card";
import { useAnalysisQuery } from "@/hooks/use-analysis";
import { useGenerateInsightsMutation, useInsightsQuery } from "@/hooks/use-insights";
import { getErrorMessage } from "@/components/layout/error-state";
import { ApiError, INSIGHT_CONTEXT_CHAR_LIMIT, type Experiment } from "@/types";

export function InsightsTab({
  projectId,
  experiment,
}: {
  projectId: number;
  experiment: Experiment;
}) {
  const { data: insights, isPending, isError, error, refetch } = useInsightsQuery(
    projectId,
    experiment.id
  );
  const { data: analysis } = useAnalysisQuery(projectId, experiment.id);
  const generateMutation = useGenerateInsightsMutation(projectId, experiment.id);

  if (isPending) return <SectionSkeleton rows={3} />;

  // A 404 here means "no Insight set generated yet" (the same deliberate
  // not-found-when-empty design as the Decision Memo endpoint) — an
  // expected state to fall through to the empty state below, not an error.
  if (isError && (!(error instanceof ApiError) || error.kind !== "not_found")) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const insightList = insights ?? [];

  if (insightList.length > 0) {
    return (
      <div className="space-y-4">
        {insightList.map((insight) => (
          <InsightCard key={insight.id} insight={insight} />
        ))}
      </div>
    );
  }

  const analysisEligible = !!analysis;

  return (
    <div className="space-y-4">
      <EmptyState
        icon={Lightbulb}
        title="No insights yet"
        description={
          analysisEligible
            ? `Generate evidence-linked insights from this experiment's completed runs. The generation context is capped at ${INSIGHT_CONTEXT_CHAR_LIMIT.toLocaleString()} characters.`
            : "Insights require completed analysis first — execute the experiment and check the Analysis tab."
        }
        action={
          analysisEligible ? (
            <Button
              onClick={() => {
                generateMutation.mutate(undefined, {
                  onSuccess: (response) => {
                    toast.success(`Generated ${response.insight_count} insights.`);
                  },
                  onError: () => toast.error("Could not generate insights."),
                });
              }}
              disabled={generateMutation.isPending}
            >
              <Sparkles /> {generateMutation.isPending ? "Generating…" : "Generate insights"}
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
