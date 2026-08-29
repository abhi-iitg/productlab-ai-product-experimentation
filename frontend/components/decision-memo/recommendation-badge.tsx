import { cn } from "@/lib/utils";
import type { Recommendation } from "@/types";

const RECOMMENDATION_LABELS: Record<Recommendation, string> = {
  proceed: "Proceed to real-user validation",
  iterate: "Iterate before validation",
  stop: "Stop investment in the current concept",
};

const RECOMMENDATION_CLASSES: Record<Recommendation, string> = {
  proceed:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  iterate:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200",
  stop: "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
};

export function RecommendationBadge({ recommendation }: { recommendation: Recommendation }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg border px-3 py-1.5 text-sm font-semibold",
        RECOMMENDATION_CLASSES[recommendation]
      )}
    >
      {RECOMMENDATION_LABELS[recommendation]}
    </span>
  );
}
