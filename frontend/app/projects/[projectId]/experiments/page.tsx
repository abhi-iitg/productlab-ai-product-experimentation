"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useMemo, useState } from "react";
import { FlaskConical, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { PageHeader } from "@/components/layout/page-header";
import { ResponsibleAiNotice } from "@/components/layout/responsible-ai-notice";
import { CardGridSkeleton } from "@/components/layout/section-skeleton";
import { ExperimentCard } from "@/components/experiments/experiment-card";
import { usePersonasQuery } from "@/hooks/use-personas";
import { useExperimentsQuery } from "@/hooks/use-experiments";
import { cn } from "@/lib/utils";
import type { ExperimentStatus } from "@/types";

const STATUS_FILTERS: { value: ExperimentStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "partially_completed", label: "Partially completed" },
  { value: "failed", label: "Failed" },
];

export default function ExperimentsPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = Number(params.projectId);

  const { data: personas } = usePersonasQuery(projectId);
  const { data: experiments, isPending, isError, error, refetch } = useExperimentsQuery(projectId);

  const [statusFilter, setStatusFilter] = useState<ExperimentStatus | "all">("all");

  const filtered = useMemo(() => {
    if (!experiments) return [];
    if (statusFilter === "all") return experiments;
    return experiments.filter((experiment) => experiment.status === statusFilter);
  }, [experiments, statusFilter]);

  const hasPersonas = (personas?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        description="Controlled A/B synthetic experiments comparing two product variants across your personas."
        actions={
          <Button nativeButton={false} render={<Link href={`/projects/${projectId}/experiments/new`} />} disabled={!hasPersonas}>
            <Plus /> New experiment
          </Button>
        }
      />

      <ResponsibleAiNotice />

      {!hasPersonas && !isPending && !isError ? (
        <p className="text-sm text-muted-foreground">
          Generate at least one persona before creating an experiment.
        </p>
      ) : null}

      {isPending ? (
        <CardGridSkeleton count={4} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : experiments.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description={
            hasPersonas
              ? "Create a two-variant experiment to simulate how your personas respond to each concept."
              : "Generate personas first, then create an experiment to compare two product variants."
          }
          action={
            hasPersonas ? (
              <Button nativeButton={false} render={<Link href={`/projects/${projectId}/experiments/new`} />}>
                <Plus /> Create your first experiment
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                onClick={() => setStatusFilter(filter.value)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  statusFilter === filter.value
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-background text-muted-foreground hover:text-foreground"
                )}
              >
                {filter.label}
              </button>
            ))}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((experiment) => (
              <ExperimentCard key={experiment.id} projectId={projectId} experiment={experiment} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
