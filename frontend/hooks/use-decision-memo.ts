import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { generateDecisionMemo, getDecisionMemo } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/types";

export function useDecisionMemoQuery(projectId: number, experimentId: number) {
  return useQuery({
    queryKey: queryKeys.decisionMemo(projectId, experimentId),
    queryFn: ({ signal }) => getDecisionMemo(projectId, experimentId, signal),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.kind === "not_found") return false;
      return failureCount < 2;
    },
  });
}

export function useGenerateDecisionMemoMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => generateDecisionMemo(projectId, experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.decisionMemo(projectId, experimentId) });
    },
  });
}
