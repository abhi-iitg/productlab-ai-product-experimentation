import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export interface WorkflowStep {
  label: string;
  complete: boolean;
}

export function WorkflowProgress({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div>
      <ol className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-0">
        {steps.map((step, index) => (
          <li key={step.label} className="flex items-center sm:flex-1">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-medium",
                  step.complete
                    ? "border-emerald-600 bg-emerald-600 text-white"
                    : "border-border bg-muted text-muted-foreground"
                )}
                aria-hidden="true"
              >
                {step.complete ? <Check className="size-3.5" /> : index + 1}
              </span>
              <span
                className={cn(
                  "text-sm",
                  step.complete ? "text-foreground" : "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 ? (
              <div className="mx-3 hidden h-px flex-1 bg-border sm:block" aria-hidden="true" />
            ) : null}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-muted-foreground">
        Workflow progress reflects available evidence, personas, and experiments only — it does
        not indicate that the concept has been validated.
      </p>
    </div>
  );
}
