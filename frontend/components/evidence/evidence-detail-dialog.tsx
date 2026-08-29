import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatusBadge } from "@/components/layout/status-badge";
import type { EvidenceItem } from "@/types";

export function EvidenceDetailDialog({
  evidence,
  open,
  onOpenChange,
}: {
  evidence: EvidenceItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        {evidence ? (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <StatusBadge status={evidence.evidence_type} />
                <span className="text-xs text-muted-foreground">Evidence #{evidence.id}</span>
              </div>
              <DialogTitle>{evidence.title}</DialogTitle>
              {evidence.source_label ? (
                <DialogDescription>Source: {evidence.source_label}</DialogDescription>
              ) : null}
            </DialogHeader>
            <p className="whitespace-pre-wrap text-sm text-foreground">{evidence.content}</p>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
