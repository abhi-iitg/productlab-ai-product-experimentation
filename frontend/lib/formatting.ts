export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString();
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function formatCost(value: string | null | undefined): string {
  if (value === null || value === undefined) return "Not configured";
  const numeric = Number.parseFloat(value);
  if (Number.isNaN(numeric)) return "Not configured";
  return numeric.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}

const LABEL_OVERRIDES: Record<string, string> = {
  interview_note: "Interview note",
  survey_response: "Survey response",
  support_ticket: "Support ticket",
  product_review: "Product review",
  research_note: "Research note",
  feature_request: "Feature request",
  partially_completed: "Partially completed",
  configuration_error: "Configuration error",
  context_limit: "Context limit exceeded",
  rate_limit: "Rate limited",
  provider_error: "Provider error",
  empty_output: "Empty output",
  malformed_json: "Malformed output",
  invalid_schema: "Invalid output schema",
  invalid_evidence_reference: "Invalid evidence reference",
  unexpected_error: "Unexpected error",
};

export function toTitleCase(value: string): string {
  if (LABEL_OVERRIDES[value]) return LABEL_OVERRIDES[value];
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
