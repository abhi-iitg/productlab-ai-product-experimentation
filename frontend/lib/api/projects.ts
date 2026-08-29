import type { Project, ProjectCreateInput, ProjectUpdateInput } from "@/types";
import { apiFetch } from "./client";

export function listProjects(signal?: AbortSignal): Promise<Project[]> {
  return apiFetch<Project[]>("/projects", { signal });
}

export function getProject(projectId: number, signal?: AbortSignal): Promise<Project> {
  return apiFetch<Project>(`/projects/${projectId}`, { signal });
}

export function createProject(input: ProjectCreateInput): Promise<Project> {
  return apiFetch<Project>("/projects", { method: "POST", body: input });
}

export function updateProject(projectId: number, input: ProjectUpdateInput): Promise<Project> {
  return apiFetch<Project>(`/projects/${projectId}`, { method: "PATCH", body: input });
}

export function deleteProject(projectId: number): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}`, { method: "DELETE" });
}
