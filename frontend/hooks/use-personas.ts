import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deletePersona, generatePersonas, listPersonas } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { PersonaGenerateInput } from "@/types";

export function usePersonasQuery(projectId: number) {
  return useQuery({
    queryKey: queryKeys.personas(projectId),
    queryFn: ({ signal }) => listPersonas(projectId, signal),
  });
}

export function useGeneratePersonasMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PersonaGenerateInput) => generatePersonas(projectId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.personas(projectId) });
    },
  });
}

export function useDeletePersonaMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (personaId: number) => deletePersona(projectId, personaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.personas(projectId) });
    },
  });
}
