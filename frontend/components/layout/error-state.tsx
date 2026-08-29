import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ApiError } from "@/types";

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export function ErrorState({
  error,
  onRetry,
  className,
  title = "Something went wrong",
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
  title?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-10 text-center",
        className
      )}
    >
      <AlertTriangle className="size-6 text-destructive" aria-hidden="true" />
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      <p className="max-w-md text-sm text-muted-foreground">{getErrorMessage(error)}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
