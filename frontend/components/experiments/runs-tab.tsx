"use client";

import { useState } from "react";
import { ListChecks } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { SectionSkeleton } from "@/components/layout/section-skeleton";
import { StatusBadge } from "@/components/layout/status-badge";
import { RunDetailDialog } from "@/components/experiments/run-detail-dialog";
import { useRunsQuery } from "@/hooks/use-runs";
import { formatCost, formatLatency, toTitleCase } from "@/lib/formatting";
import { cn } from "@/lib/utils";
import type { Experiment, Persona, SimulationRun } from "@/types";

export function RunsTab({
  projectId,
  experiment,
  personas,
}: {
  projectId: number;
  experiment: Experiment;
  personas: Persona[];
}) {
  const { data: runs, isPending, isError, error, refetch } = useRunsQuery(
    projectId,
    experiment.id
  );
  const [selectedRun, setSelectedRun] = useState<SimulationRun | null>(null);

  const variantLabel = (variantId: number) => {
    const variant = experiment.variants.find((v) => v.id === variantId);
    return variant ? `${variant.key} · ${variant.name}` : `Variant #${variantId}`;
  };
  const personaName = (personaId: number) =>
    personas.find((p) => p.id === personaId)?.name ?? `Persona #${personaId}`;

  if (isPending) return <SectionSkeleton rows={5} />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (runs.length === 0) {
    return (
      <EmptyState
        icon={ListChecks}
        title="No runs yet"
        description="Execute this experiment from the Overview tab to generate simulation runs."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="hidden overflow-x-auto rounded-xl border border-border sm:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Variant</TableHead>
              <TableHead>Persona</TableHead>
              <TableHead>Rep</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Outcome</TableHead>
              <TableHead>Clarity</TableHead>
              <TableHead>Value</TableHead>
              <TableHead>Adoption</TableHead>
              <TableHead>Latency</TableHead>
              <TableHead>Tokens</TableHead>
              <TableHead>Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow
                key={run.id}
                className={cn(
                  "cursor-pointer",
                  run.status === "failed" && "bg-destructive/5"
                )}
                onClick={() => setSelectedRun(run)}
              >
                <TableCell>{variantLabel(run.variant_id)}</TableCell>
                <TableCell>{personaName(run.persona_id)}</TableCell>
                <TableCell>{run.repetition_index}</TableCell>
                <TableCell>
                  <StatusBadge status={run.status} />
                </TableCell>
                <TableCell>
                  {run.task_outcome ? (
                    <StatusBadge status={run.task_outcome} />
                  ) : run.failure_type ? (
                    <span className="text-xs text-destructive">
                      {toTitleCase(run.failure_type)}
                    </span>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell>{run.clarity_score ?? "—"}</TableCell>
                <TableCell>{run.perceived_value_score ?? "—"}</TableCell>
                <TableCell>{run.adoption_intent_score ?? "—"}</TableCell>
                <TableCell>{formatLatency(run.latency_ms)}</TableCell>
                <TableCell>
                  {run.input_tokens ?? "—"}/{run.output_tokens ?? "—"}
                </TableCell>
                <TableCell>{formatCost(run.estimated_cost_usd)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 sm:hidden">
        {runs.map((run) => (
          <button
            key={run.id}
            type="button"
            onClick={() => setSelectedRun(run)}
            className={cn(
              "w-full rounded-xl border border-border bg-card p-4 text-left ring-1 ring-foreground/10",
              run.status === "failed" && "border-destructive/30 bg-destructive/5"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-foreground">
                {variantLabel(run.variant_id)}
              </span>
              <StatusBadge status={run.status} />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {personaName(run.persona_id)} · rep {run.repetition_index}
            </p>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>Clarity {run.clarity_score ?? "—"}</span>
              <span>Value {run.perceived_value_score ?? "—"}</span>
              <span>Adoption {run.adoption_intent_score ?? "—"}</span>
              <span>{formatLatency(run.latency_ms)}</span>
              <span>{formatCost(run.estimated_cost_usd)}</span>
            </div>
          </button>
        ))}
      </div>

      <RunDetailDialog
        run={selectedRun}
        variantLabel={selectedRun ? variantLabel(selectedRun.variant_id) : ""}
        personaName={selectedRun ? personaName(selectedRun.persona_id) : ""}
        open={!!selectedRun}
        onOpenChange={(open) => !open && setSelectedRun(null)}
      />
    </div>
  );
}
