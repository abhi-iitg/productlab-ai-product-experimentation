import type { EvidenceItem, EvidenceItemCreateInput, EvidenceItemUpdateInput } from "@/types";
import { apiFetch } from "./client";

export function listEvidence(projectId: number, signal?: AbortSignal): Promise<EvidenceItem[]> {
  return apiFetch<EvidenceItem[]>(`/projects/${projectId}/evidence`, { signal });
}

export function getEvidenceItem(
  projectId: number,
  evidenceId: number,
  signal?: AbortSignal
): Promise<EvidenceItem> {
  return apiFetch<EvidenceItem>(`/projects/${projectId}/evidence/${evidenceId}`, { signal });
}

export function createEvidenceItem(
  projectId: number,
  input: EvidenceItemCreateInput
): Promise<EvidenceItem> {
  return apiFetch<EvidenceItem>(`/projects/${projectId}/evidence`, {
    method: "POST",
    body: input,
  });
}

export function updateEvidenceItem(
  projectId: number,
  evidenceId: number,
  input: EvidenceItemUpdateInput
): Promise<EvidenceItem> {
  return apiFetch<EvidenceItem>(`/projects/${projectId}/evidence/${evidenceId}`, {
    method: "PATCH",
    body: input,
  });
}

export function deleteEvidenceItem(projectId: number, evidenceId: number): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}/evidence/${evidenceId}`, { method: "DELETE" });
}
