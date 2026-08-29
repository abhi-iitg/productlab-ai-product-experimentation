import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createExperiment, listExperiments } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ExperimentCreateInput } from "@/types";

export function useExperimentsQuery(projectId: number) {
  return useQuery({
    queryKey: queryKeys.experiments(projectId),
    queryFn: ({ signal }) => listExperiments(projectId, signal),
  });
}

export function useCreateExperimentMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ExperimentCreateInput) => createExperiment(projectId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments(projectId) });
    },
  });
}
