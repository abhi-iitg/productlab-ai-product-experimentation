import { useQuery } from "@tanstack/react-query";

import { listRuns } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useRunsQuery(projectId: number, experimentId: number) {
  return useQuery({
    queryKey: queryKeys.runs(projectId, experimentId),
    queryFn: ({ signal }) => listRuns(projectId, experimentId, signal),
  });
}
