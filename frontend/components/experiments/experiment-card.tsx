import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/layout/status-badge";
import { formatDate } from "@/lib/formatting";
import type { Experiment } from "@/types";

export function ExperimentCard({
  projectId,
  experiment,
}: {
  projectId: number;
  experiment: Experiment;
}) {
  const plannedRuns = experiment.persona_ids.length * 2 * experiment.repeat_count;

  return (
    <Link
      href={`/projects/${projectId}/experiments/${experiment.id}`}
      className="group block rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Card className="h-full transition-shadow group-hover:shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base">{experiment.name}</CardTitle>
            <StatusBadge status={experiment.status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Objective</p>
            <p className="line-clamp-2 text-sm text-foreground">{experiment.objective}</p>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>{experiment.persona_ids.length} personas</span>
            <span>×{experiment.repeat_count} repeats</span>
            <span>{plannedRuns} planned runs</span>
          </div>
          <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
            <span>Created {formatDate(experiment.created_at)}</span>
            <span className="inline-flex items-center gap-1 font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
              Open <ArrowRight className="size-3.5" />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
