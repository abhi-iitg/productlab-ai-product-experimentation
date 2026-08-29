import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { toTitleCase } from "@/lib/formatting";

type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "border-border bg-muted text-foreground",
  info: "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  success:
    "border-transparent bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  warning:
    "border-transparent bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
  danger: "border-transparent bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

const STATUS_TONES: Record<string, Tone> = {
  draft: "neutral",
  active: "success",
  archived: "neutral",
  running: "info",
  completed: "success",
  partially_completed: "warning",
  failed: "danger",
  uncertain: "warning",
  low: "neutral",
  medium: "info",
  high: "success",
  proceed: "success",
  iterate: "warning",
  stop: "danger",
  A: "info",
  B: "info",
  both: "neutral",
  aligned: "success",
  not_aligned: "warning",
  insufficient_data: "neutral",
  A_higher: "info",
  B_higher: "info",
  equal: "neutral",
};

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: string;
  label?: string;
  className?: string;
}) {
  const tone = STATUS_TONES[status] ?? "neutral";
  return (
    <Badge
      variant="outline"
      className={cn(TONE_CLASSES[tone], "font-medium", className)}
    >
      {label ?? toTitleCase(status)}
    </Badge>
  );
}
