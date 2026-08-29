import { cn } from "@/lib/utils";

export function MetricBar({
  label,
  value,
  displayValue,
  className,
}: {
  label: string;
  /** 0-1 fraction of the bar to fill. */
  value: number | null;
  displayValue: string;
  className?: string;
}) {
  const percent = value === null ? 0 : Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium text-foreground">{displayValue}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" role="presentation">
        <div
          className={cn("h-full rounded-full", value === null ? "bg-transparent" : "bg-primary")}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
