import { useQuery } from "@tanstack/react-query";

import { getAnalysis } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/types";

export function useAnalysisQuery(projectId: number, experimentId: number, enabled = true) {
  return useQuery({
    queryKey: queryKeys.analysis(projectId, experimentId),
    queryFn: ({ signal }) => getAnalysis(projectId, experimentId, signal),
    enabled,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && (error.kind === "validation" || error.kind === "conflict")) {
        return false;
      }
      return failureCount < 2;
    },
  });
}
