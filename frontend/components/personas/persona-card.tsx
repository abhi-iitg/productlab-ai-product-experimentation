import { AlertTriangle, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/layout/status-badge";
import type { Persona } from "@/types";

function PersonaListSection({ title, items }: { title: string; items: string[] }) {
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

export function PersonaCard({ persona, onDelete }: { persona: Persona; onDelete: () => void }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle>{persona.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{persona.segment_label}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={persona.confidence_level} label={`${persona.confidence_level} confidence`} />
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Delete persona ${persona.name}`}
              className="text-destructive hover:text-destructive"
              onClick={onDelete}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-foreground">{persona.summary}</p>

        <div className="grid gap-4 sm:grid-cols-2">
          <PersonaListSection title="Goals" items={persona.goals} />
          <PersonaListSection title="Pain points" items={persona.pain_points} />
          <PersonaListSection title="Constraints" items={persona.constraints} />
          <PersonaListSection title="Behaviors" items={persona.behaviors} />
        </div>

        <Separator />

        <div>
          <p className="text-xs font-medium text-muted-foreground">Evidence-backed claims</p>
          <ul className="mt-1 space-y-2">
            {persona.evidence_references.map((reference) => (
              <li key={reference.evidence_item_id} className="text-sm">
                <span className="font-medium text-foreground">
                  Evidence #{reference.evidence_item_id}:
                </span>{" "}
                <span className="text-muted-foreground">
                  {reference.supported_claims.join("; ")}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {persona.unsupported_assumptions.length > 0 ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
            <p className="flex items-center gap-1.5 text-xs font-medium text-amber-900 dark:text-amber-200">
              <AlertTriangle className="size-3.5" /> Unsupported assumptions
            </p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-amber-900 dark:text-amber-200">
              {persona.unsupported_assumptions.map((assumption) => (
                <li key={assumption}>{assumption}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none">Generation details</summary>
          <p className="mt-1">Prompt version: {persona.prompt_version}</p>
          <p>Model: {persona.model_name}</p>
        </details>
      </CardContent>
    </Card>
  );
}
