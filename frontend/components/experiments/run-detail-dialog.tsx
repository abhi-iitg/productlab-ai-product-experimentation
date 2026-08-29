import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatusBadge } from "@/components/layout/status-badge";
import { formatLatency, toTitleCase } from "@/lib/formatting";
import type { SimulationRun } from "@/types";

function DetailList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">{title}</p>
      <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function RunDetailDialog({
  run,
  variantLabel,
  personaName,
  open,
  onOpenChange,
}: {
  run: SimulationRun | null;
  variantLabel: string;
  personaName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        {run ? (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <StatusBadge status={run.status} />
                {run.task_outcome ? <StatusBadge status={run.task_outcome} /> : null}
              </div>
              <DialogTitle>
                {variantLabel} · {personaName} · repetition {run.repetition_index}
              </DialogTitle>
              <DialogDescription>Run #{run.id}</DialogDescription>
            </DialogHeader>

            {run.status === "failed" ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                <p className="font-medium">
                  {run.failure_type ? toTitleCase(run.failure_type) : "Failure"}
                </p>
                {run.failure_message ? <p className="mt-1">{run.failure_message}</p> : null}
              </div>
            ) : (
              <div className="space-y-4">
                {run.response_summary ? (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Response summary</p>
                    <p className="mt-1 text-sm text-foreground">{run.response_summary}</p>
                  </div>
                ) : null}

                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="rounded-lg border border-border p-2">
                    <p className="text-xs text-muted-foreground">Clarity</p>
                    <p className="font-medium">{run.clarity_score ?? "—"}/5</p>
                  </div>
                  <div className="rounded-lg border border-border p-2">
                    <p className="text-xs text-muted-foreground">Value</p>
                    <p className="font-medium">{run.perceived_value_score ?? "—"}/5</p>
                  </div>
                  <div className="rounded-lg border border-border p-2">
                    <p className="text-xs text-muted-foreground">Adoption</p>
                    <p className="font-medium">{run.adoption_intent_score ?? "—"}/5</p>
                  </div>
                </div>

                <DetailList title="Positive signals" items={run.positive_signals} />
                <DetailList title="Objections" items={run.objections} />
                <DetailList title="Confusion points" items={run.confusion_points} />
                <DetailList title="Feature requests" items={run.feature_requests} />
                <DetailList title="Uncertainty notes" items={run.uncertainty_notes} />

                {run.evidence_references.length > 0 ? (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Evidence references</p>
                    <ul className="mt-1 space-y-1 text-sm text-foreground">
                      {run.evidence_references.map((reference) => (
                        <li key={reference.evidence_item_id}>
                          Evidence #{reference.evidence_item_id}:{" "}
                          {reference.supported_claims.join("; ")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}

            <div className="grid grid-cols-2 gap-x-4 gap-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
              <span>Prompt version: {run.prompt_version}</span>
              <span>Model: {run.model_name}</span>
              <span>Latency: {formatLatency(run.latency_ms)}</span>
              <span>
                Tokens: {run.input_tokens ?? "—"} in / {run.output_tokens ?? "—"} out
              </span>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
