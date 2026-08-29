import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createEvidenceItem,
  deleteEvidenceItem,
  listEvidence,
  updateEvidenceItem,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { EvidenceItemCreateInput, EvidenceItemUpdateInput } from "@/types";

export function useEvidenceQuery(projectId: number) {
  return useQuery({
    queryKey: queryKeys.evidence(projectId),
    queryFn: ({ signal }) => listEvidence(projectId, signal),
  });
}

export function useCreateEvidenceMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EvidenceItemCreateInput) => createEvidenceItem(projectId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.evidence(projectId) });
    },
  });
}

export function useUpdateEvidenceMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ evidenceId, input }: { evidenceId: number; input: EvidenceItemUpdateInput }) =>
      updateEvidenceItem(projectId, evidenceId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.evidence(projectId) });
    },
  });
}

export function useDeleteEvidenceMutation(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: number) => deleteEvidenceItem(projectId, evidenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.evidence(projectId) });
    },
  });
}
