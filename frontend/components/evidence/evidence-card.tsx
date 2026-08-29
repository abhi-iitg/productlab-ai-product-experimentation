import { Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/layout/status-badge";
import { formatDate } from "@/lib/formatting";
import type { EvidenceItem } from "@/types";

export function EvidenceCard({
  evidence,
  onView,
  onEdit,
  onDelete,
}: {
  evidence: EvidenceItem;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <StatusBadge status={evidence.evidence_type} />
              <span className="text-xs text-muted-foreground">#{evidence.id}</span>
            </div>
            <button
              type="button"
              onClick={onView}
              className="text-left text-sm font-medium text-foreground hover:underline"
            >
              {evidence.title}
            </button>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button variant="ghost" size="icon-sm" aria-label="Edit evidence" onClick={onEdit}>
              <Pencil className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Delete evidence"
              className="text-destructive hover:text-destructive"
              onClick={onDelete}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="line-clamp-3 text-sm text-muted-foreground">{evidence.content}</p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{evidence.source_label ?? "No source label"}</span>
          <span>Added {formatDate(evidence.created_at)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
