import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricBar } from "@/components/analytics/metric-bar";
import { formatCost, formatInteger, formatLatency, formatPercent } from "@/lib/formatting";
import type { Variant, VariantMetrics } from "@/types";

const OUTCOME_LABELS: { key: keyof VariantMetrics["task_outcome_distribution"]; label: string }[] = [
  { key: "completed", label: "Completed" },
  { key: "partially_completed", label: "Partially completed" },
  { key: "failed", label: "Failed" },
  { key: "uncertain", label: "Uncertain" },
];

function VariantCard({ variant, metrics }: { variant?: Variant; metrics: VariantMetrics }) {
  const totalOutcomes = Object.values(metrics.task_outcome_distribution).reduce(
    (sum, count) => sum + count,
    0
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Variant {metrics.variant_key}
          {variant ? `: ${variant.name}` : ""}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Completed runs</p>
            <p className="font-medium text-foreground">{formatInteger(metrics.completed_run_count)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Failed runs</p>
            <p className="font-medium text-foreground">{formatInteger(metrics.failed_run_count)}</p>
          </div>
        </div>

        <MetricBar
          label="Task completion rate"
          value={metrics.task_completion_rate}
          displayValue={formatPercent(metrics.task_completion_rate)}
        />
        <MetricBar
          label="Average clarity"
          value={metrics.average_clarity_score !== null ? metrics.average_clarity_score / 5 : null}
          displayValue={
            metrics.average_clarity_score !== null ? `${metrics.average_clarity_score.toFixed(1)} / 5` : "—"
          }
        />
        <MetricBar
          label="Average perceived value"
          value={
            metrics.average_perceived_value_score !== null
              ? metrics.average_perceived_value_score / 5
              : null
          }
          displayValue={
            metrics.average_perceived_value_score !== null
              ? `${metrics.average_perceived_value_score.toFixed(1)} / 5`
              : "—"
          }
        />
        <MetricBar
          label="Average adoption intent"
          value={
            metrics.average_adoption_intent_score !== null
              ? metrics.average_adoption_intent_score / 5
              : null
          }
          displayValue={
            metrics.average_adoption_intent_score !== null
              ? `${metrics.average_adoption_intent_score.toFixed(1)} / 5`
              : "—"
          }
        />

        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">Task outcomes</p>
          <div className="space-y-1.5">
            {OUTCOME_LABELS.map(({ key, label }) => {
              const count = metrics.task_outcome_distribution[key];
              return (
                <MetricBar
                  key={key}
                  label={label}
                  value={totalOutcomes > 0 ? count / totalOutcomes : null}
                  displayValue={String(count)}
                />
              );
            })}
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-3 border-t border-border pt-3 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Average latency</dt>
            <dd className="font-medium text-foreground">{formatLatency(metrics.average_latency_ms)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Estimated cost</dt>
            <dd className="font-medium text-foreground">{formatCost(metrics.total_estimated_cost_usd)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Input tokens</dt>
            <dd className="font-medium text-foreground">{formatInteger(metrics.total_input_tokens)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Output tokens</dt>
            <dd className="font-medium text-foreground">{formatInteger(metrics.total_output_tokens)}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

export function VariantComparison({
  variantMetrics,
  variants,
}: {
  variantMetrics: VariantMetrics[];
  variants: Variant[];
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {variantMetrics
        .slice()
        .sort((a, b) => a.variant_key.localeCompare(b.variant_key))
        .map((metrics) => (
          <VariantCard
            key={metrics.variant_id}
            metrics={metrics}
            variant={variants.find((v) => v.id === metrics.variant_id)}
          />
        ))}
    </div>
  );
}
