import type { AnalyticsResponse, DecisionMemo, Insight, InsightGenerateResponse } from "@/types";
import { apiFetch } from "./client";

export function getAnalysis(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<AnalyticsResponse> {
  return apiFetch<AnalyticsResponse>(
    `/projects/${projectId}/experiments/${experimentId}/analysis`,
    { signal }
  );
}

export function listInsights(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<Insight[]> {
  return apiFetch<Insight[]>(`/projects/${projectId}/experiments/${experimentId}/insights`, {
    signal,
  });
}

export function generateInsights(
  projectId: number,
  experimentId: number
): Promise<InsightGenerateResponse> {
  return apiFetch<InsightGenerateResponse>(
    `/projects/${projectId}/experiments/${experimentId}/insights/generate`,
    { method: "POST" }
  );
}

export function getDecisionMemo(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<DecisionMemo> {
  return apiFetch<DecisionMemo>(
    `/projects/${projectId}/experiments/${experimentId}/decision-memo`,
    { signal }
  );
}

export function generateDecisionMemo(
  projectId: number,
  experimentId: number
): Promise<DecisionMemo> {
  return apiFetch<DecisionMemo>(
    `/projects/${projectId}/experiments/${experimentId}/decision-memo/generate`,
    { method: "POST" }
  );
}
