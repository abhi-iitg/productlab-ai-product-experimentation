import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/layout/status-badge";
import type { Insight } from "@/types";

export function InsightCard({ insight }: { insight: Insight }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={insight.category} />
          <StatusBadge
            status={insight.variant_scope}
            label={insight.variant_scope === "both" ? "Both variants" : `Variant ${insight.variant_scope}`}
          />
          <StatusBadge status={insight.confidence_level} label={`${insight.confidence_level} confidence`} />
        </div>
        <CardTitle className="text-base">{insight.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-foreground">{insight.summary}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>Frequency: {insight.frequency}</span>
          <span>Personas: {insight.persona_count}</span>
          <span>Runs: {insight.supporting_run_ids.map((id) => `#${id}`).join(", ")}</span>
          {insight.supporting_evidence_ids.length > 0 ? (
            <span>
              Evidence: {insight.supporting_evidence_ids.map((id) => `#${id}`).join(", ")}
            </span>
          ) : null}
        </div>
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none">Generation details</summary>
          <p className="mt-1">Prompt version: {insight.prompt_version}</p>
          <p>Model: {insight.model_name}</p>
        </details>
      </CardContent>
    </Card>
  );
}
