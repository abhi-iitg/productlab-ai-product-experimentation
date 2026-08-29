import type { Persona, PersonaGenerateInput, PersonaGenerateResponse } from "@/types";
import { apiFetch } from "./client";

export function listPersonas(projectId: number, signal?: AbortSignal): Promise<Persona[]> {
  return apiFetch<Persona[]>(`/projects/${projectId}/personas`, { signal });
}

export function getPersona(
  projectId: number,
  personaId: number,
  signal?: AbortSignal
): Promise<Persona> {
  return apiFetch<Persona>(`/projects/${projectId}/personas/${personaId}`, { signal });
}

export function generatePersonas(
  projectId: number,
  input: PersonaGenerateInput
): Promise<PersonaGenerateResponse> {
  return apiFetch<PersonaGenerateResponse>(`/projects/${projectId}/personas/generate`, {
    method: "POST",
    body: input,
  });
}

export function deletePersona(projectId: number, personaId: number): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}/personas/${personaId}`, { method: "DELETE" });
}
