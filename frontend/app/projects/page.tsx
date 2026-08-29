"use client";

import Link from "next/link";
import { FolderPlus, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { PageHeader } from "@/components/layout/page-header";
import { CardGridSkeleton } from "@/components/layout/section-skeleton";
import { ProjectCard } from "@/components/projects/project-card";
import { useProjectsQuery } from "@/hooks/use-projects";

export default function ProjectsPage() {
  const { data: projects, isPending, isError, error, refetch } = useProjectsQuery();

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <PageHeader
        title="Projects"
        description="Product briefs and their evidence, personas, and experiments."
        actions={
          <Button nativeButton={false} render={<Link href="/projects/new" />}>
            <Plus /> New project
          </Button>
        }
      />

      {isPending ? (
        <CardGridSkeleton count={6} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : projects.length === 0 ? (
        <EmptyState
          icon={FolderPlus}
          title="No projects yet"
          description="Start by creating a project brief — the problem, target user, hypothesis, and success metric that everything else builds on."
          action={
            <Button nativeButton={false} render={<Link href="/projects/new" />}>
              <Plus /> Create your first project
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}
