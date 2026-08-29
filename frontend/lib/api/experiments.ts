import type {
  Experiment,
  ExperimentCreateInput,
  ExperimentExecutionSummary,
  ExperimentUpdateInput,
  SimulationRun,
} from "@/types";
import { apiFetch } from "./client";

export function listExperiments(
  projectId: number,
  signal?: AbortSignal
): Promise<Experiment[]> {
  return apiFetch<Experiment[]>(`/projects/${projectId}/experiments`, { signal });
}

export function getExperiment(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<Experiment> {
  return apiFetch<Experiment>(`/projects/${projectId}/experiments/${experimentId}`, { signal });
}

export function createExperiment(
  projectId: number,
  input: ExperimentCreateInput
): Promise<Experiment> {
  return apiFetch<Experiment>(`/projects/${projectId}/experiments`, {
    method: "POST",
    body: input,
  });
}

export function updateExperiment(
  projectId: number,
  experimentId: number,
  input: ExperimentUpdateInput
): Promise<Experiment> {
  return apiFetch<Experiment>(`/projects/${projectId}/experiments/${experimentId}`, {
    method: "PATCH",
    body: input,
  });
}

export function deleteExperiment(projectId: number, experimentId: number): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}/experiments/${experimentId}`, {
    method: "DELETE",
  });
}

export function executeExperiment(
  projectId: number,
  experimentId: number
): Promise<ExperimentExecutionSummary> {
  return apiFetch<ExperimentExecutionSummary>(
    `/projects/${projectId}/experiments/${experimentId}/execute`,
    { method: "POST", body: { confirm_execution: true } }
  );
}

export function listRuns(
  projectId: number,
  experimentId: number,
  signal?: AbortSignal
): Promise<SimulationRun[]> {
  return apiFetch<SimulationRun[]>(`/projects/${projectId}/experiments/${experimentId}/runs`, {
    signal,
  });
}

export function getRun(
  projectId: number,
  experimentId: number,
  runId: number,
  signal?: AbortSignal
): Promise<SimulationRun> {
  return apiFetch<SimulationRun>(
    `/projects/${projectId}/experiments/${experimentId}/runs/${runId}`,
    { signal }
  );
}
