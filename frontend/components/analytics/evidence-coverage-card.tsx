import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricBar } from "@/components/analytics/metric-bar";
import type { EvidenceCoverage } from "@/types";

export function EvidenceCoverageCard({ coverage }: { coverage: EvidenceCoverage }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Evidence citation coverage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <MetricBar
          label={`${coverage.completed_runs_with_evidence} of ${coverage.completed_runs_total} completed runs cite evidence`}
          value={coverage.evidence_citation_rate}
          displayValue={
            coverage.evidence_citation_rate !== null
              ? `${Math.round(coverage.evidence_citation_rate * 100)}%`
              : "—"
          }
        />
        <div>
          <p className="text-xs text-muted-foreground">
            {coverage.unique_cited_evidence_ids.length} unique evidence item
            {coverage.unique_cited_evidence_ids.length === 1 ? "" : "s"} cited
          </p>
          {coverage.unique_cited_evidence_ids.length > 0 ? (
            <p className="mt-1 text-xs text-foreground">
              {coverage.unique_cited_evidence_ids.map((id) => `#${id}`).join(", ")}
            </p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
