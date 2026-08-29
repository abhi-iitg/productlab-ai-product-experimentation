import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/layout/status-badge";
import { formatDate } from "@/lib/formatting";
import type { Project } from "@/types";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="group block rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Card className="h-full transition-shadow group-hover:shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base">{project.name}</CardTitle>
            <StatusBadge status={project.status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Target user</p>
            <p className="line-clamp-2 text-sm text-foreground">{project.target_user}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Success metric</p>
            <p className="line-clamp-1 text-sm text-foreground">{project.success_metric}</p>
          </div>
          <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
            <span>Updated {formatDate(project.updated_at)}</span>
            <span className="inline-flex items-center gap-1 font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
              Open <ArrowRight className="size-3.5" />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
