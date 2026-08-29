import { AlertTriangle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatInteger, formatPercent } from "@/lib/formatting";
import type { ExperimentCoverage } from "@/types";

export function CoverageSummary({ coverage }: { coverage: ExperimentCoverage }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Run coverage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="text-xs text-muted-foreground">Expected runs</p>
            <p className="text-lg font-semibold text-foreground">
              {formatInteger(coverage.expected_runs)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Persisted runs</p>
            <p className="text-lg font-semibold text-foreground">
              {formatInteger(coverage.total_persisted_runs)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Completion rate</p>
            <p className="text-lg font-semibold text-foreground">
              {formatPercent(coverage.completion_rate)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Represented personas</p>
            <p className="text-lg font-semibold text-foreground">
              {formatInteger(coverage.represented_persona_count)}
            </p>
          </div>
        </div>

        {coverage.data_quality_warnings.length > 0 ? (
          <div className="space-y-1.5 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
            {coverage.data_quality_warnings.map((warning) => (
              <p
                key={warning}
                className="flex items-start gap-1.5 text-sm text-amber-900 dark:text-amber-200"
              >
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {warning}
              </p>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
