import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteExperiment, executeExperiment, getExperiment, updateExperiment } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ExperimentUpdateInput } from "@/types";

export function useExperimentQuery(projectId: number, experimentId: number) {
  return useQuery({
    queryKey: queryKeys.experiment(projectId, experimentId),
    queryFn: ({ signal }) => getExperiment(projectId, experimentId, signal),
  });
}

export function useUpdateExperimentMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ExperimentUpdateInput) => updateExperiment(projectId, experimentId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiment(projectId, experimentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments(projectId) });
    },
  });
}

export function useDeleteExperimentMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteExperiment(projectId, experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments(projectId) });
      queryClient.removeQueries({ queryKey: queryKeys.experiment(projectId, experimentId) });
    },
  });
}

export function useExecuteExperimentMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => executeExperiment(projectId, experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiment(projectId, experimentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.runs(projectId, experimentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.analysis(projectId, experimentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments(projectId) });
    },
  });
}
