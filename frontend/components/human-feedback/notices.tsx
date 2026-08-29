import { ShieldAlert, Users } from "lucide-react";

import { cn } from "@/lib/utils";

const NOTICE_CLASSES =
  "flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200";

export const PRIVACY_NOTICE =
  "Enter anonymized feedback only. Do not include participant names, emails, phone numbers, account identifiers, demographic data, or other personally identifiable information — use a pseudonymous label such as \"Participant 1\" or \"Interview P3\" instead.";

export const QUALITATIVE_SAMPLE_NOTICE =
  "Real-participant feedback entered into this platform may represent a small qualitative sample. The comparison supports learning; it does not establish statistical significance or market validation.";

export function PrivacyNotice({ className }: { className?: string }) {
  return (
    <div role="note" className={cn(NOTICE_CLASSES, className)}>
      <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p>{PRIVACY_NOTICE}</p>
    </div>
  );
}

export function QualitativeSampleNotice({ className }: { className?: string }) {
  return (
    <div role="note" className={cn(NOTICE_CLASSES, className)}>
      <Users className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p>{QUALITATIVE_SAMPLE_NOTICE}</p>
    </div>
  );
}

export function InterpretationNotice({
  message,
  className,
}: {
  message: string;
  className?: string;
}) {
  return (
    <div role="note" className={cn(NOTICE_CLASSES, className)}>
      <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}
