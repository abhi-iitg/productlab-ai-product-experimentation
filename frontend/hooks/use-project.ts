import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteProject, getProject, updateProject } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ProjectUpdateInput } from "@/types";

export function useProjectQuery(projectId: number) {
  return useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: ({ signal }) => getProject(projectId, signal),
  });
}

export function useUpdateProjectMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ProjectUpdateInput) => updateProject(projectId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.projects() });
    },
  });
}

export function useDeleteProjectMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects() });
      queryClient.removeQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}
