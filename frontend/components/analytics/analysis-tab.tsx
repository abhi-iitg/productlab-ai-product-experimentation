"use client";

import { BarChart3 } from "lucide-react";

import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { CoverageSummary } from "@/components/analytics/coverage-summary";
import { VariantComparison } from "@/components/analytics/variant-comparison";
import { ThemeCountsCard } from "@/components/analytics/theme-counts-card";
import { EvidenceCoverageCard } from "@/components/analytics/evidence-coverage-card";
import { FailureBreakdownCard } from "@/components/analytics/failure-breakdown-card";
import { PersonaDisagreementCard } from "@/components/analytics/persona-disagreement-card";
import { useAnalysisQuery } from "@/hooks/use-analysis";
import { ApiError, type Experiment, type Persona } from "@/types";

export function AnalysisTab({
  projectId,
  experiment,
  personas,
}: {
  projectId: number;
  experiment: Experiment;
  personas: Persona[];
}) {
  const { data: analysis, isPending, isError, error, refetch } = useAnalysisQuery(
    projectId,
    experiment.id
  );

  if (isPending) return <SectionSkeleton rows={4} />;

  if (isError) {
    if (error instanceof ApiError && error.kind === "conflict") {
      return (
        <EmptyState
          icon={BarChart3}
          title="Analysis not available yet"
          description={error.message}
        />
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-4">
      <CoverageSummary coverage={analysis.coverage} />
      <VariantComparison variantMetrics={analysis.variant_metrics} variants={experiment.variants} />
      <ThemeCountsCard themeCounts={analysis.deterministic_theme_counts} />
      <div className="grid gap-4 sm:grid-cols-2">
        <EvidenceCoverageCard coverage={analysis.evidence_coverage} />
        <FailureBreakdownCard breakdown={analysis.failure_breakdown} />
      </div>
      <PersonaDisagreementCard disagreement={analysis.persona_disagreement} personas={personas} />
    </div>
  );
}
