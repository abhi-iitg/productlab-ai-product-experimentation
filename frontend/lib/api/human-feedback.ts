import type {
  HumanComparisonResponse,
  HumanFeedback,
  HumanFeedbackCreateInput,
  HumanFeedbackUpdateInput,
} from "@/types";
import { apiFetch } from "./client";

export function listHumanFeedback(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<HumanFeedback[]> {
  return apiFetch<HumanFeedback[]>(
    `/projects/${projectId}/experiments/${experimentId}/human-feedback`,
    { signal }
  );
}

export function createHumanFeedback(
  projectId: number,
  experimentId: number,
  input: HumanFeedbackCreateInput
): Promise<HumanFeedback> {
  return apiFetch<HumanFeedback>(
    `/projects/${projectId}/experiments/${experimentId}/human-feedback`,
    { method: "POST", body: input }
  );
}

export function updateHumanFeedback(
  projectId: number,
  experimentId: number,
  feedbackId: number,
  input: HumanFeedbackUpdateInput
): Promise<HumanFeedback> {
  return apiFetch<HumanFeedback>(
    `/projects/${projectId}/experiments/${experimentId}/human-feedback/${feedbackId}`,
    { method: "PATCH", body: input }
  );
}

export function deleteHumanFeedback(
  projectId: number,
  experimentId: number,
  feedbackId: number
): Promise<void> {
  return apiFetch<void>(
    `/projects/${projectId}/experiments/${experimentId}/human-feedback/${feedbackId}`,
    { method: "DELETE" }
  );
}

export function getHumanComparison(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<HumanComparisonResponse> {
  return apiFetch<HumanComparisonResponse>(
    `/projects/${projectId}/experiments/${experimentId}/human-feedback/comparison`,
    { signal }
  );
}
