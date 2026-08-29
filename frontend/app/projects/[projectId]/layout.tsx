"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FolderX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { StatusBadge } from "@/components/layout/status-badge";
import { ProjectNav } from "@/components/projects/project-nav";
import { useProjectQuery } from "@/hooks/use-project";
import { ApiError } from "@/types";

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ projectId: string }>();
  const projectId = Number(params.projectId);
  const { data: project, isPending, isError, error, refetch } = useProjectQuery(projectId);

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      {isPending ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-8 w-full max-w-md" />
        </div>
      ) : isError ? (
        error instanceof ApiError && error.kind === "not_found" ? (
          <EmptyState
            icon={FolderX}
            title="Project not found"
            description="It may have been deleted, or the link may be incorrect."
            action={
              <Button variant="outline" nativeButton={false} render={<Link href="/projects" />}>
                Back to projects
              </Button>
            }
          />
        ) : (
          <ErrorState error={error} onRetry={() => refetch()} title="Could not load project" />
        )
      ) : (
        <>
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
                {project.name}
              </h1>
              <StatusBadge status={project.status} />
            </div>
            <ProjectNav projectId={projectId} />
          </div>
          {children}
        </>
      )}
    </div>
  );
}
