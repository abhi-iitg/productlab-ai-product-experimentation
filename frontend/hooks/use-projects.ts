import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProject, listProjects } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ProjectCreateInput } from "@/types";

export function useProjectsQuery() {
  return useQuery({
    queryKey: queryKeys.projects(),
    queryFn: ({ signal }) => listProjects(signal),
  });
}

export function useCreateProjectMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ProjectCreateInput) => createProject(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects() });
    },
  });
}
