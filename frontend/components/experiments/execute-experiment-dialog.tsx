"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getErrorMessage } from "@/components/layout/error-state";
import { useExecuteExperimentMutation } from "@/hooks/use-experiment";

export function ExecuteExperimentDialog({
  projectId,
  experimentId,
  plannedRuns,
  open,
  onOpenChange,
}: {
  projectId: number;
  experimentId: number;
  plannedRuns: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useExecuteExperimentMutation(projectId, experimentId);

  return (
    <Dialog open={open} onOpenChange={(next) => !mutation.isPending && onOpenChange(next)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Execute this experiment?</DialogTitle>
          <DialogDescription>
            This will run {plannedRuns} simulations across both variants.
          </DialogDescription>
        </DialogHeader>

        <ul className="list-inside list-disc space-y-1.5 text-sm text-foreground">
          <li>Execution runs synchronously — this dialog stays open until it finishes.</li>
          <li>Once started, the experiment&apos;s settings become immutable.</li>
          <li>Individual run failures are preserved and shown, not hidden or retried.</li>
          <li>Synthetic results do not replace real-user testing.</li>
        </ul>

        {mutation.isError ? (
          <p
            role="alert"
            className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {getErrorMessage(mutation.error)}
          </p>
        ) : null}

        <DialogFooter>
          <Button
            onClick={() => {
              mutation.mutate(undefined, {
                onSuccess: (summary) => {
                  toast.success(
                    `Execution finished: ${summary.completed_runs} completed, ${summary.failed_runs} failed.`
                  );
                  onOpenChange(false);
                },
                onError: () => toast.error("Execution could not be started."),
              });
            }}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Executing…" : "Confirm and execute"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
