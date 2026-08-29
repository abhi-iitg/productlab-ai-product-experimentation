"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { FileText, FlaskConical, Trash2, UsersRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { EditProjectSheet } from "@/components/projects/edit-project-sheet";
import { WorkflowProgress } from "@/components/projects/workflow-progress";
import { useDeleteProjectMutation, useProjectQuery, useUpdateProjectMutation } from "@/hooks/use-project";
import { useEvidenceQuery } from "@/hooks/use-evidence";
import { usePersonasQuery } from "@/hooks/use-personas";
import { useExperimentsQuery } from "@/hooks/use-experiments";
import type { ProjectStatus } from "@/types";

const STATUS_OPTIONS: { value: ProjectStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
];

export default function ProjectOverviewPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = Number(params.projectId);
  const router = useRouter();

  const { data: project } = useProjectQuery(projectId);
  const { data: evidence } = useEvidenceQuery(projectId);
  const { data: personas } = usePersonasQuery(projectId);
  const { data: experiments } = useExperimentsQuery(projectId);

  const updateMutation = useUpdateProjectMutation(projectId);
  const deleteMutation = useDeleteProjectMutation(projectId);

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (!project) return null;

  const steps = [
    { label: "Evidence added", complete: (evidence?.length ?? 0) > 0 },
    { label: "Personas generated", complete: (personas?.length ?? 0) > 0 },
    { label: "Experiment created", complete: (experiments?.length ?? 0) > 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Select
          value={project.status}
          onValueChange={(value) => {
            updateMutation.mutate(
              { status: value as ProjectStatus },
              {
                onSuccess: () => toast.success("Project status updated."),
                onError: () => toast.error("Could not update status."),
              }
            );
          }}
        >
          <SelectTrigger aria-label="Project status" size="sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
          Edit project
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          onClick={() => setDeleteOpen(true)}
        >
          <Trash2 /> Delete
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <WorkflowProgress steps={steps} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Problem statement</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-foreground">
                {project.problem_statement}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Product hypothesis</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-foreground">
                {project.product_hypothesis}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Target user</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-foreground">{project.target_user}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Assumptions</CardTitle>
            </CardHeader>
            <CardContent>
              {project.assumptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No assumptions recorded.</p>
              ) : (
                <ul className="list-inside list-disc space-y-1 text-sm text-foreground">
                  {project.assumptions.map((assumption) => (
                    <li key={assumption}>{assumption}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Success metric</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-foreground">{project.success_metric}</p>
            </CardContent>
          </Card>

          <nav aria-label="Project areas" className="space-y-3">
            <Link
              href={`/projects/${projectId}/evidence`}
              className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm ring-1 ring-foreground/10 transition-colors hover:bg-muted"
            >
              <span className="flex items-center gap-2 font-medium text-foreground">
                <FileText className="size-4 text-muted-foreground" /> Evidence
              </span>
              <span className="text-muted-foreground">{evidence?.length ?? 0}</span>
            </Link>
            <Link
              href={`/projects/${projectId}/personas`}
              className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm ring-1 ring-foreground/10 transition-colors hover:bg-muted"
            >
              <span className="flex items-center gap-2 font-medium text-foreground">
                <UsersRound className="size-4 text-muted-foreground" /> Personas
              </span>
              <span className="text-muted-foreground">{personas?.length ?? 0}</span>
            </Link>
            <Link
              href={`/projects/${projectId}/experiments`}
              className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm ring-1 ring-foreground/10 transition-colors hover:bg-muted"
            >
              <span className="flex items-center gap-2 font-medium text-foreground">
                <FlaskConical className="size-4 text-muted-foreground" /> Experiments
              </span>
              <span className="text-muted-foreground">{experiments?.length ?? 0}</span>
            </Link>
          </nav>
        </div>
      </div>

      <EditProjectSheet project={project} open={editOpen} onOpenChange={setEditOpen} />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete this project?"
        description={`This permanently deletes "${project.name}" and all of its evidence, personas, and experiments. This cannot be undone.`}
        confirmLabel="Delete project"
        destructive
        confirming={deleteMutation.isPending}
        onConfirm={() => {
          deleteMutation.mutate(undefined, {
            onSuccess: () => {
              toast.success("Project deleted.");
              router.push("/projects");
            },
            onError: () => toast.error("Could not delete project."),
          });
        }}
      />
    </div>
  );
}
