"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FlaskConical } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { PageHeader } from "@/components/layout/page-header";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { StatusBadge } from "@/components/layout/status-badge";
import { OverviewTab } from "@/components/experiments/overview-tab";
import { RunsTab } from "@/components/experiments/runs-tab";
import { AnalysisTab } from "@/components/analytics/analysis-tab";
import { InsightsTab } from "@/components/analytics/insights-tab";
import { DecisionMemoTab } from "@/components/decision-memo/decision-memo-tab";
import { RealFeedbackTab } from "@/components/human-feedback/real-feedback-tab";
import { useExperimentQuery } from "@/hooks/use-experiment";
import { usePersonasQuery } from "@/hooks/use-personas";
import { ApiError } from "@/types";

export default function ExperimentDetailPage() {
  const params = useParams<{ projectId: string; experimentId: string }>();
  const projectId = Number(params.projectId);
  const experimentId = Number(params.experimentId);

  const { data: experiment, isPending, isError, error, refetch } = useExperimentQuery(
    projectId,
    experimentId
  );
  const { data: personas } = usePersonasQuery(projectId);

  if (isPending) {
    return (
      <div className="space-y-4">
        <SectionSkeleton rows={1} />
        <SectionSkeleton rows={4} />
      </div>
    );
  }

  if (isError) {
    if (error instanceof ApiError && error.kind === "not_found") {
      return (
        <EmptyState
          icon={FlaskConical}
          title="Experiment not found"
          description="It may have been deleted, or the link may be incorrect."
          action={
            <Button variant="outline" nativeButton={false} render={<Link href={`/projects/${projectId}/experiments`} />}>
              Back to experiments
            </Button>
          }
        />
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} title="Could not load experiment" />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {experiment.name}
            <StatusBadge status={experiment.status} />
          </span>
        }
        description={experiment.objective}
      />

      <Tabs defaultValue="overview">
        <TabsList variant="line">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="insights">Insights</TabsTrigger>
          <TabsTrigger value="decision-memo">Decision Memo</TabsTrigger>
          <TabsTrigger value="real-feedback">Real Feedback</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="pt-4">
          <OverviewTab projectId={projectId} experiment={experiment} personas={personas ?? []} />
        </TabsContent>
        <TabsContent value="runs" className="pt-4">
          <RunsTab projectId={projectId} experiment={experiment} personas={personas ?? []} />
        </TabsContent>
        <TabsContent value="analysis" className="pt-4">
          <AnalysisTab projectId={projectId} experiment={experiment} personas={personas ?? []} />
        </TabsContent>
        <TabsContent value="insights" className="pt-4">
          <InsightsTab projectId={projectId} experiment={experiment} />
        </TabsContent>
        <TabsContent value="decision-memo" className="pt-4">
          <DecisionMemoTab projectId={projectId} experiment={experiment} />
        </TabsContent>
        <TabsContent value="real-feedback" className="pt-4">
          <RealFeedbackTab projectId={projectId} experiment={experiment} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
