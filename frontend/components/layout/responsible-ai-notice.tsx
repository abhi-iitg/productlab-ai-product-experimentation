import { ShieldAlert } from "lucide-react";

import { cn } from "@/lib/utils";

export const RESPONSIBLE_AI_NOTICE =
  "Synthetic feedback supports hypothesis generation and experiment planning. It does not replace real-user research or predict market success.";

export function ResponsibleAiNotice({ className }: { className?: string }) {
  return (
    <div
      role="note"
      className={cn(
        "flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200",
        className
      )}
    >
      <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p>{RESPONSIBLE_AI_NOTICE}</p>
    </div>
  );
}
