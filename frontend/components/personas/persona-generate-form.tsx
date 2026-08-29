"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge } from "@/components/layout/status-badge";
import { cn } from "@/lib/utils";
import {
  personaGenerateFormSchema,
  type PersonaGenerateFormValues,
} from "@/lib/validation/persona";
import type { EvidenceItem, PersonaGenerateInput } from "@/types";

const PERSONA_CONTEXT_CHAR_LIMIT = 20_000;

export function PersonaGenerateForm({
  evidence,
  submitting,
  onSubmit,
}: {
  evidence: EvidenceItem[];
  submitting: boolean;
  onSubmit: (input: PersonaGenerateInput) => void;
}) {
  const form = useForm<PersonaGenerateFormValues>({
    resolver: zodResolver(personaGenerateFormSchema),
    defaultValues: {
      persona_count: 3,
      evidence_scope: "all",
      selected_evidence_ids: [],
      focus: "",
    },
  });

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors },
  } = form;

  const scope = useWatch({ control, name: "evidence_scope" });
  const selectedIds = useWatch({ control, name: "selected_evidence_ids" });
  const personaCount = useWatch({ control, name: "persona_count" });
  const totalChars = evidence.reduce((sum, item) => sum + item.content.length, 0);

  return (
    <form
      onSubmit={handleSubmit((values) => {
        onSubmit({
          persona_count: values.persona_count,
          selected_evidence_ids: values.evidence_scope === "all" ? null : values.selected_evidence_ids,
          focus: values.focus && values.focus.length > 0 ? values.focus : null,
        });
      })}
      className="space-y-5"
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="persona_count">Number of personas</Label>
        <Select
          value={String(personaCount)}
          onValueChange={(value) => setValue("persona_count", Number(value), { shouldValidate: true })}
        >
          <SelectTrigger id="persona_count" className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[2, 3, 4, 5].map((count) => (
              <SelectItem key={count} value={String(count)}>
                {count}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Evidence to use</Label>
        <div className="flex gap-2">
          <Button
            type="button"
            variant={scope === "all" ? "secondary" : "outline"}
            size="sm"
            onClick={() => setValue("evidence_scope", "all")}
          >
            Use all evidence ({evidence.length})
          </Button>
          <Button
            type="button"
            variant={scope === "selected" ? "secondary" : "outline"}
            size="sm"
            onClick={() => setValue("evidence_scope", "selected")}
          >
            Select specific evidence
          </Button>
        </div>

        {scope === "selected" ? (
          <div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-border p-2">
            {evidence.map((item) => {
              const checked = selectedIds.includes(item.id);
              return (
                <label
                  key={item.id}
                  className={cn(
                    "flex cursor-pointer items-start gap-2 rounded-md p-2 text-sm hover:bg-muted",
                    checked && "bg-muted"
                  )}
                >
                  <Checkbox
                    checked={checked}
                    onCheckedChange={(value) => {
                      const next = value
                        ? [...selectedIds, item.id]
                        : selectedIds.filter((id) => id !== item.id);
                      setValue("selected_evidence_ids", next, { shouldValidate: true });
                    }}
                    className="mt-0.5"
                  />
                  <span className="flex-1">
                    <span className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{item.title}</span>
                      <StatusBadge status={item.evidence_type} />
                    </span>
                    <span className="line-clamp-1 text-xs text-muted-foreground">
                      #{item.id} · {item.content.length.toLocaleString()} characters
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Total evidence content: {totalChars.toLocaleString()} characters.
          </p>
        )}
        {errors.selected_evidence_ids ? (
          <p className="text-sm text-destructive">{errors.selected_evidence_ids.message}</p>
        ) : null}
        <p className="text-xs text-muted-foreground">
          The generation context is capped at {PERSONA_CONTEXT_CHAR_LIMIT.toLocaleString()}{" "}
          characters. If the selected evidence exceeds that limit, generation will fail —
          select fewer or shorter items.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="focus">Focus (optional)</Label>
        <Textarea
          id="focus"
          rows={2}
          placeholder="e.g. Focus on onboarding friction for self-serve users"
          {...register("focus")}
        />
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={submitting || evidence.length === 0}>
          {submitting ? "Generating…" : "Generate personas"}
        </Button>
      </div>
    </form>
  );
}
