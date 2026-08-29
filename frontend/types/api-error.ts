export type ApiErrorKind =
  | "not_found"
  | "conflict"
  | "validation"
  | "provider_error"
  | "provider_unavailable"
  | "network"
  | "unknown";

export interface ApiFieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly fieldErrors: ApiFieldError[];

  constructor(
    message: string,
    kind: ApiErrorKind,
    status: number | null = null,
    fieldErrors: ApiFieldError[] = []
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}
