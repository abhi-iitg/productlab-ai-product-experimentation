import { ApiError, type ApiErrorKind, type ApiFieldError } from "@/types/api-error";
import { buildApiUrl } from "./config";

const STATUS_TO_KIND: Record<number, ApiErrorKind> = {
  404: "not_found",
  409: "conflict",
  422: "validation",
  502: "provider_error",
  503: "provider_unavailable",
};

const FALLBACK_MESSAGES: Partial<Record<ApiErrorKind, string>> = {
  not_found: "The requested resource could not be found.",
  conflict: "This action conflicts with the resource's current state.",
  validation: "The request was invalid.",
  provider_error: "The AI provider was unable to complete the request.",
  provider_unavailable: "The AI provider is not configured.",
  network: "Unable to reach the API. Check that the backend is running.",
  unknown: "Something went wrong. Please try again.",
};

interface ParsedErrorBody {
  message: string;
  fieldErrors: ApiFieldError[];
}

function parseValidationDetail(detail: unknown[]): ParsedErrorBody {
  const fieldErrors: ApiFieldError[] = detail.map((item) => {
    const entry = item as { loc?: unknown; msg?: unknown };
    const loc = Array.isArray(entry.loc)
      ? entry.loc.filter((part) => part !== "body").map(String)
      : [];
    return {
      field: loc.length > 0 ? loc.join(".") : "request",
      message: typeof entry.msg === "string" ? entry.msg : "Invalid value.",
    };
  });
  const message =
    fieldErrors.length > 0
      ? fieldErrors.map((error) => error.message).join(" ")
      : FALLBACK_MESSAGES.validation!;
  return { message, fieldErrors };
}

async function parseErrorBody(response: Response, kind: ApiErrorKind): Promise<ParsedErrorBody> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  const detail = (body as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string" && detail.trim().length > 0) {
    return { message: detail, fieldErrors: [] };
  }
  if (Array.isArray(detail)) {
    return parseValidationDetail(detail);
  }
  return { message: FALLBACK_MESSAGES[kind] ?? FALLBACK_MESSAGES.unknown!, fieldErrors: [] };
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * Centralized fetch wrapper for every backend call. Never expose stack
 * traces or raw provider internals — only the backend's `detail` message
 * (or a safe fallback) ever reaches a thrown ApiError.
 */
export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;

  let response: Response;
  try {
    response = await fetch(buildApiUrl(path), {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(FALLBACK_MESSAGES.network!, "network");
  }

  if (!response.ok) {
    const kind = STATUS_TO_KIND[response.status] ?? "unknown";
    const { message, fieldErrors } = await parseErrorBody(response, kind);
    throw new ApiError(message, kind, response.status, fieldErrors);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (text.length === 0) {
    return undefined as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError("The server returned an unexpected response.", "unknown");
  }
}
