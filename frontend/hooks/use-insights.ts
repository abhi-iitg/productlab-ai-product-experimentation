import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { generateInsights, listInsights } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useInsightsQuery(projectId: number, experimentId: number) {
  return useQuery({
    queryKey: queryKeys.insights(projectId, experimentId),
    queryFn: ({ signal }) => listInsights(projectId, experimentId, signal),
  });
}

export function useGenerateInsightsMutation(projectId: number, experimentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => generateInsights(projectId, experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.insights(projectId, experimentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.analysis(projectId, experimentId) });
    },
  });
}
