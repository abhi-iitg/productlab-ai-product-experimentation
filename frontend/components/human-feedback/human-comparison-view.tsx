import { AlertTriangle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MetricBar } from "@/components/analytics/metric-bar";
import { StatusBadge } from "@/components/layout/status-badge";
import { InterpretationNotice } from "@/components/human-feedback/notices";
import { formatInteger, formatPercent, toTitleCase } from "@/lib/formatting";
import type {
  HumanComparisonResponse,
  QualitativeCategory,
  SyntheticVariantSummary,
  HumanVariantSummary,
} from "@/types";

const QUALITATIVE_LABELS: Record<QualitativeCategory, string> = {
  positive_signals: "Positive signals",
  objections: "Objections",
  confusion_points: "Confusion points",
  feature_requests: "Feature requests",
  uncertainty_notes: "Uncertainty notes",
};

function scoreBar(label: string, score: number | null) {
  return (
    <MetricBar
      label={label}
      value={score !== null ? score / 5 : null}
      displayValue={score !== null ? `${score.toFixed(1)} / 5` : "—"}
    />
  );
}

function VariantSampleCard({
  synthetic,
  human,
}: {
  synthetic: SyntheticVariantSummary;
  human: HumanVariantSummary;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Variant {synthetic.variant_key}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Synthetic sample</p>
            <p className="font-medium text-foreground">
              {formatInteger(synthetic.completed_run_count)} completed runs
            </p>
            <p className="text-xs text-muted-foreground">
              {formatInteger(synthetic.represented_persona_count)} personas
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Real-participant sample</p>
            <p className="font-medium text-foreground">
              {formatInteger(human.feedback_record_count)} feedback records
            </p>
            <p className="text-xs text-muted-foreground">
              {formatInteger(human.unique_participant_count)} participants
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground">Synthetic averages</p>
            {scoreBar("Clarity", synthetic.average_clarity_score)}
            {scoreBar("Perceived value", synthetic.average_perceived_value_score)}
            {scoreBar("Adoption intent", synthetic.average_adoption_intent_score)}
          </div>
          <div className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground">Real-participant averages</p>
            {scoreBar("Clarity", human.average_clarity_score)}
            {scoreBar("Perceived value", human.average_perceived_value_score)}
            {scoreBar("Adoption intent", human.average_adoption_intent_score)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function TaskOutcomeTable({ comparison }: { comparison: HumanComparisonResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Task completion rates</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Variant</TableHead>
                <TableHead>Synthetic rate</TableHead>
                <TableHead>Real-participant rate</TableHead>
                <TableHead>Absolute difference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {comparison.task_outcome_comparisons.map((row) => (
                <TableRow key={row.variant_key}>
                  <TableCell>Variant {row.variant_key}</TableCell>
                  <TableCell>{formatPercent(row.synthetic_completion_rate)}</TableCell>
                  <TableCell>{formatPercent(row.human_completion_rate)}</TableCell>
                  <TableCell>
                    {row.absolute_difference !== null
                      ? `${(row.absolute_difference * 100).toFixed(0)} pp`
                      : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          A percentage-point difference only — not a test of statistical significance.
        </p>
      </CardContent>
    </Card>
  );
}

function MetricDirectionTable({ comparison }: { comparison: HumanComparisonResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Score-direction agreement</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead>Synthetic direction</TableHead>
                <TableHead>Real-participant direction</TableHead>
                <TableHead>Alignment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {comparison.metric_direction_comparisons.map((row) => (
                <TableRow key={row.metric}>
                  <TableCell>{toTitleCase(row.metric)}</TableCell>
                  <TableCell>{toTitleCase(row.synthetic_direction)}</TableCell>
                  <TableCell>{toTitleCase(row.human_direction)}</TableCell>
                  <TableCell>
                    <StatusBadge status={row.alignment} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Direction agreement only — this does not test statistical significance or predictive
          accuracy.
        </p>
      </CardContent>
    </Card>
  );
}

function ThemeComparisonTable({ comparison }: { comparison: HumanComparisonResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Theme comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-border p-3 text-center">
            <p className="text-xs text-muted-foreground">Shared themes</p>
            <p className="text-lg font-semibold text-foreground">{comparison.shared_theme_count}</p>
          </div>
          <div className="rounded-md border border-border p-3 text-center">
            <p className="text-xs text-muted-foreground">Synthetic-only themes</p>
            <p className="text-lg font-semibold text-foreground">
              {comparison.synthetic_only_theme_count}
            </p>
          </div>
          <div className="rounded-md border border-border p-3 text-center">
            <p className="text-xs text-muted-foreground">Real-only themes</p>
            <p className="text-lg font-semibold text-foreground">
              {comparison.human_only_theme_count}
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead>Variant</TableHead>
                <TableHead>Shared</TableHead>
                <TableHead>Synthetic-only</TableHead>
                <TableHead>Real-only</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {comparison.theme_comparisons.map((row) => (
                <TableRow key={`${row.category}-${row.variant_key}`}>
                  <TableCell className="whitespace-nowrap">
                    {QUALITATIVE_LABELS[row.category]}
                  </TableCell>
                  <TableCell>{row.variant_key}</TableCell>
                  <TableCell>
                    {row.shared_themes.length > 0 ? row.shared_themes.join(", ") : "—"}
                  </TableCell>
                  <TableCell>
                    {row.synthetic_only_themes.length > 0
                      ? row.synthetic_only_themes.join(", ")
                      : "—"}
                  </TableCell>
                  <TableCell>
                    {row.human_only_themes.length > 0 ? row.human_only_themes.join(", ") : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

export function HumanComparisonView({ comparison }: { comparison: HumanComparisonResponse }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {comparison.variant_comparisons.map((row) => (
          <VariantSampleCard key={row.variant_key} synthetic={row.synthetic} human={row.human} />
        ))}
      </div>

      <TaskOutcomeTable comparison={comparison} />
      <MetricDirectionTable comparison={comparison} />
      <ThemeComparisonTable comparison={comparison} />

      {comparison.data_quality_warnings.length > 0 ? (
        <div className="space-y-1.5 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
          {comparison.data_quality_warnings.map((warning) => (
            <p
              key={warning}
              className="flex items-start gap-1.5 text-sm text-amber-900 dark:text-amber-200"
            >
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {warning}
            </p>
          ))}
        </div>
      ) : null}

      <InterpretationNotice message={comparison.interpretation_notice} />
    </div>
  );
}
