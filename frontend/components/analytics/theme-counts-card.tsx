import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ThemeCounts, VariantKey } from "@/types";

const THEME_LABELS: { key: keyof ThemeCounts; label: string }[] = [
  { key: "positive_signals", label: "Positive signals" },
  { key: "objections", label: "Objections" },
  { key: "confusion_points", label: "Confusion points" },
  { key: "feature_requests", label: "Feature requests" },
  { key: "uncertainty_notes", label: "Uncertainty notes" },
];

export function ThemeCountsCard({
  themeCounts,
}: {
  themeCounts: Partial<Record<VariantKey, ThemeCounts>>;
}) {
  const variantKeys = (Object.keys(themeCounts) as VariantKey[]).sort();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recurring signals</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[24rem] text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th scope="col" className="py-1.5 pr-4 font-medium">
                  Signal
                </th>
                {variantKeys.map((key) => (
                  <th key={key} scope="col" className="py-1.5 pr-4 font-medium">
                    Variant {key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {THEME_LABELS.map(({ key, label }) => (
                <tr key={key} className="border-b border-border/60 last:border-0">
                  <th scope="row" className="py-1.5 pr-4 text-left font-normal text-foreground">
                    {label}
                  </th>
                  {variantKeys.map((variantKey) => (
                    <td key={variantKey} className="py-1.5 pr-4 text-foreground">
                      {themeCounts[variantKey]?.[key] ?? 0}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Deterministic verbatim counts across completed runs — no clustering or semantic
          grouping.
        </p>
      </CardContent>
    </Card>
  );
}
