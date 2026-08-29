import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createHumanFeedback,
  deleteHumanFeedback,
  getHumanComparison,
  listHumanFeedback,
  updateHumanFeedback,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/types";
import type { HumanFeedbackCreateInput, HumanFeedbackUpdateInput } from "@/types";

export function useHumanFeedbackQuery(projectId: number, experimentId: number) {
  return useQuery({
    queryKey: queryKeys.humanFeedback(projectId, experimentId),
    queryFn: ({ signal }) => listHumanFeedback(projectId, experimentId, signal),
  });
}

export function useHumanComparisonQuery(projectId: number, experimentId: number) {
  return useQuery({
    queryKey: queryKeys.humanComparison(projectId, experimentId),
    queryFn: ({ signal }) => getHumanComparison(projectId, experimentId, signal),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && ["not_found", "conflict", "validation"].includes(error.kind)) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

function invalidateFeedbackAndComparison(
  queryClient: ReturnType<typeof useQueryClient>,
  projectId: number,
  experimentId: number
) {
  queryClient.invalidateQueries({ queryKey: queryKeys.humanFeedback(projectId, experimentId) });
  queryClient.invalidateQueries({ queryKey: queryKeys.humanComparison(projectId, experimentId) });
}

export function useCreateHumanFeedbackMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: HumanFeedbackCreateInput) =>
      createHumanFeedback(projectId, experimentId, input),
    onSuccess: () => invalidateFeedbackAndComparison(queryClient, projectId, experimentId),
  });
}

export function useUpdateHumanFeedbackMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      feedbackId,
      input,
    }: {
      feedbackId: number;
      input: HumanFeedbackUpdateInput;
    }) => updateHumanFeedback(projectId, experimentId, feedbackId, input),
    onSuccess: () => invalidateFeedbackAndComparison(queryClient, projectId, experimentId),
  });
}

export function useDeleteHumanFeedbackMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (feedbackId: number) => deleteHumanFeedback(projectId, experimentId, feedbackId),
    onSuccess: () => invalidateFeedbackAndComparison(queryClient, projectId, experimentId),
  });
}
