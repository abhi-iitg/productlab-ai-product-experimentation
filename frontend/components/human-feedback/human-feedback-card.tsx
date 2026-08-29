import { Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/layout/status-badge";
import { formatDate, toTitleCase } from "@/lib/formatting";
import type { HumanFeedback, QualitativeCategory } from "@/types";

const QUALITATIVE_LABELS: Record<QualitativeCategory, string> = {
  positive_signals: "Positive signals",
  objections: "Objections",
  confusion_points: "Confusion points",
  feature_requests: "Feature requests",
  uncertainty_notes: "Uncertainty notes",
};

function QualitativeList({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <ul className="list-inside list-disc space-y-0.5 text-sm text-foreground">
        {values.map((value) => (
          <li key={value}>{value}</li>
        ))}
      </ul>
    </div>
  );
}

export function HumanFeedbackCard({
  feedback,
  onEdit,
  onDelete,
}: {
  feedback: HumanFeedback;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {feedback.participant_label}
              </span>
              <StatusBadge status={feedback.variant_key} label={`Variant ${feedback.variant_key}`} />
              <StatusBadge status={feedback.task_outcome} />
            </div>
            <p className="text-xs text-muted-foreground">
              {toTitleCase(feedback.source_method)}
              {feedback.session_date ? ` · ${formatDate(feedback.session_date)}` : ""}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button variant="ghost" size="icon-sm" aria-label="Edit feedback" onClick={onEdit}>
              <Pencil className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Delete feedback"
              className="text-destructive hover:text-destructive"
              onClick={onDelete}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-3 gap-2 text-center text-sm">
          <div className="rounded-md border border-border p-2">
            <dt className="text-xs text-muted-foreground">Clarity</dt>
            <dd className="font-semibold text-foreground">{feedback.clarity_score}/5</dd>
          </div>
          <div className="rounded-md border border-border p-2">
            <dt className="text-xs text-muted-foreground">Perceived value</dt>
            <dd className="font-semibold text-foreground">{feedback.perceived_value_score}/5</dd>
          </div>
          <div className="rounded-md border border-border p-2">
            <dt className="text-xs text-muted-foreground">Adoption intent</dt>
            <dd className="font-semibold text-foreground">{feedback.adoption_intent_score}/5</dd>
          </div>
        </dl>

        <p className="text-sm text-foreground">{feedback.feedback_summary}</p>

        <div className="grid gap-3 sm:grid-cols-2">
          {(Object.keys(QUALITATIVE_LABELS) as QualitativeCategory[]).map((category) => (
            <QualitativeList
              key={category}
              label={QUALITATIVE_LABELS[category]}
              values={feedback[category]}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
