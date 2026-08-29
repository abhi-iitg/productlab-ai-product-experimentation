"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { StatusBadge } from "@/components/layout/status-badge";
import { EditExperimentSheet } from "@/components/experiments/edit-experiment-sheet";
import { ExecuteExperimentDialog } from "@/components/experiments/execute-experiment-dialog";
import { useDeleteExperimentMutation } from "@/hooks/use-experiment";
import { formatDateTime } from "@/lib/formatting";
import type { Experiment, Persona } from "@/types";

export function OverviewTab({
  projectId,
  experiment,
  personas,
}: {
  projectId: number;
  experiment: Experiment;
  personas: Persona[];
}) {
  const router = useRouter();
  const deleteMutation = useDeleteExperimentMutation(projectId, experiment.id);

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [executeOpen, setExecuteOpen] = useState(false);

  const isDraft = experiment.status === "draft";
  const plannedRuns = experiment.persona_ids.length * 2 * experiment.repeat_count;
  const selectedPersonas = personas.filter((persona) => experiment.persona_ids.includes(persona.id));

  return (
    <div className="space-y-6">
      {isDraft ? (
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 /> Delete
          </Button>
          <Button size="sm" onClick={() => setExecuteOpen(true)}>
            <Play /> Execute experiment
          </Button>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Objective</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-foreground">{experiment.objective}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hypothesis</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-foreground">{experiment.hypothesis}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Shared scenario</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-foreground">{experiment.scenario}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Evaluation criteria</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm text-foreground">
                {experiment.evaluation_criteria.map((criterion) => (
                  <li key={criterion}>{criterion}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
          <div className="grid gap-4 sm:grid-cols-2">
            {experiment.variants
              .slice()
              .sort((a, b) => a.key.localeCompare(b.key))
              .map((variant) => (
                <Card key={variant.id}>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Variant {variant.key}: {variant.name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap text-sm text-foreground">
                      {variant.description}
                    </p>
                  </CardContent>
                </Card>
              ))}
          </div>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <StatusBadge status={experiment.status} />
              <dl className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <dt>Created</dt>
                  <dd>{formatDateTime(experiment.created_at)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Started</dt>
                  <dd>{formatDateTime(experiment.started_at)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Completed</dt>
                  <dd>{formatDateTime(experiment.completed_at)}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Run plan</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-foreground">
              <p>{selectedPersonas.length} personas</p>
              <p>2 variants</p>
              <p>×{experiment.repeat_count} repeats</p>
              <p className="font-medium">{plannedRuns} total planned runs</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Personas</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm text-foreground">
                {selectedPersonas.map((persona) => (
                  <li key={persona.id}>{persona.name}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>

      <EditExperimentSheet
        projectId={projectId}
        experiment={experiment}
        personas={personas}
        open={editOpen}
        onOpenChange={setEditOpen}
      />

      <ExecuteExperimentDialog
        projectId={projectId}
        experimentId={experiment.id}
        plannedRuns={plannedRuns}
        open={executeOpen}
        onOpenChange={setExecuteOpen}
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete this experiment?"
        description={`"${experiment.name}" will be permanently removed. This cannot be undone.`}
        confirmLabel="Delete experiment"
        destructive
        confirming={deleteMutation.isPending}
        onConfirm={() => {
          deleteMutation.mutate(undefined, {
            onSuccess: () => {
              toast.success("Experiment deleted.");
              router.push(`/projects/${projectId}/experiments`);
            },
            onError: () => toast.error("Could not delete experiment."),
          });
        }}
      />
    </div>
  );
}
