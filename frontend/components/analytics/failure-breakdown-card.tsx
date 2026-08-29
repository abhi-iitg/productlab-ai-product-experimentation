import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toTitleCase } from "@/lib/formatting";
import type { FailureBreakdown } from "@/types";

export function FailureBreakdownCard({ breakdown }: { breakdown: FailureBreakdown }) {
  const entries = Object.entries(breakdown.counts_by_category).filter(([, count]) => count > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Failure breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        {breakdown.total_failed_runs === 0 ? (
          <p className="text-sm text-muted-foreground">No failed runs.</p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {entries.map(([category, count]) => (
              <li key={category} className="flex items-center justify-between">
                <span className="text-foreground">{toTitleCase(category)}</span>
                <span className="font-medium text-foreground">{count}</span>
              </li>
            ))}
            <li className="flex items-center justify-between border-t border-border pt-1.5 text-xs text-muted-foreground">
              <span>Total failed runs</span>
              <span>{breakdown.total_failed_runs}</span>
            </li>
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
