# Decision Framework

This document describes the framework implemented end-to-end by
`DecisionMemoService` (`backend/app/services/decision_memo.py`), including
the exact recommendation definitions and the deterministic decision-safety
rules enforced after every provider response.

## Purpose

This document defines how the platform interprets and communicates
Proceed / Iterate / Stop recommendations, and how it handles uncertainty and
unsupported findings so synthetic feedback is never presented as market
validation.

## Interpreting Proceed / Iterate / Stop

These are the exact meanings supplied to the LLM provider (see
`app/llm/decision_prompts.py`) and enforced by `DecisionMemoService`:

- **Proceed** — The current concept or variant has enough synthetic signal
  to justify moving into real-user validation. It does **not** mean launch.
  The memo's `executive_summary` must explicitly say the next step is
  real-user validation — this is checked, not just instructed.
- **Iterate** — Important assumptions, confusion, objections, or evidence
  gaps should be addressed before real-user validation.
- **Stop** — The current concept or hypothesis should not receive further
  investment in its present form. This does not prove that the broader
  market opportunity is invalid.
- In all three cases, the memo states its recommendation as a starting
  hypothesis for further real-user testing, never as a final verdict.

## Decision Safety Rules (enforced in `DecisionMemoService`, after schema validation)

These rules are re-checked in code after every provider response — a
model is instructed to follow them, but instructions alone are never
trusted as the sole safeguard. A violation raises a `ProviderError`
(`502 Bad Gateway`) and the memo is not persisted.

1. **Proceed must name real-user validation, not launch.** When
   `recommendation` is `proceed`, `executive_summary` must contain the
   phrase "real-user validation" (case-insensitive).
2. **Severe data-quality warnings block Proceed.** When the experiment's
   `data_quality_flags` (from `ExperimentAnalyticsService`) show any of:
   a variant with zero completed runs, severe run-failure imbalance (more
   than half of persisted runs failed), or fewer than two represented
   personas — `proceed` is rejected outright; the model must choose
   `iterate` or `stop` instead.
3. **No evidence citations requires an uncertainty warning and an
   evidence-collection recommendation.** When no completed run in the
   experiment cites supporting evidence (`data_quality_flags
   .no_evidence_citations`), the memo must include at least one item under
   `uncertain_conclusions`, and the word "evidence" must appear somewhere
   in the memo's free text (e.g. a recommended product change or the
   real-user test objective) — a concrete, checkable proxy for "recommend
   collecting real evidence."
4. **No market-validation or launch-readiness claims, ever.** Every
   free-text field is scanned (case-insensitively) for a fixed set of
   forbidden phrases — including "product-market fit," "proves market
   demand," "validates market demand," "predicts market success," "ready
   to launch," "ready for launch," "approved for launch," "launch
   readiness," and "guaranteed conversion" — and rejected if any appear,
   regardless of the selected recommendation.

There is no hidden numeric recommendation score anywhere in this pipeline —
these are explicit, individually testable rules over analytics flags and
memo text, not a weighted formula.

## Evidence Requirements

- Every persona must cite the evidence items it was grounded in. Attributes
  not traceable to any evidence item must be listed as explicit unsupported
  assumptions rather than presented as evidence-backed.
- Every simulation result retains a reference back to the persona and the
  evidence that grounded it, so any finding in the decision memo can be
  traced to its evidence source.
- Findings that cannot be traced to evidence are never used as "supporting
  findings" for a Proceed recommendation — they can only appear under
  flagged uncertainty or unsupported findings.

## Uncertainty Handling

- Each structured simulation result records an explicit `uncertainty_notes`
  list, tracked separately from clear objections; `ExperimentAnalyticsService`
  counts these per variant (`deterministic_theme_counts`) alongside a
  dedicated, non-averaged `persona_disagreement` metric — for every persona
  with completed runs against both variants, its preferred variant and
  whether that preference diverges from the experiment's overall direction.
- The Decision Memo's own `uncertain_conclusions` field is where the model
  is instructed to surface high uncertainty or high persona disagreement,
  and it is required (checked in code, not just prompted) to be non-empty
  whenever no completed run cites supporting evidence (Decision Safety Rule
  3 above).

## Unsupported / Low-Confidence Finding Handling

- Every `Insight` records its own `confidence_level` (`low` / `medium` /
  `high`) based on how directly its supporting runs support it, and a
  dedicated `category` value of `uncertainty` for findings that shouldn't be
  stated as grounded — set by the model, per the Insight-generation prompt
  rule to place unsupported interpretation under uncertainty rather than a
  confident category (`strength`, `objection`, etc.).
- Findings a model surfaces without traceable `supporting_evidence_ids` are
  never blocked from becoming an Insight (a strength or objection observed
  purely from a persona's *behavior* in a run is still real signal) — but
  every `supporting_run_ids` and `supporting_evidence_ids` reference is
  locally validated before persistence, so a decision memo reader can always
  trace an Insight back to the exact runs (and, where cited, evidence) that
  produced it via the Insight and SimulationRun APIs.
- The Decision Memo's `uncertain_conclusions` field is the reader-facing
  place low-confidence or unsupported findings are called out explicitly —
  never merged into `supporting_findings`.

## Why Synthetic Findings Cannot Independently Validate a Market

Synthetic personas are generated from a necessarily limited evidence
library and simulated by a language model that can produce
plausible-sounding but ungrounded responses. They cannot:

- capture real willingness to pay or genuine behavioral commitment,
- represent users or market segments not reflected in the evidence library,
- account for real-world context (timing, competition, price sensitivity,
  switching cost) outside the text evidence provided,
- guarantee that model-generated agreement reflects genuine user consensus
  rather than model bias or prompt framing.

For these reasons, the decision memo is framed as an evidence-organizing and
hypothesis-refining tool, not a market-validation verdict, consistent with
the responsible-AI notice used throughout this project:

> "Synthetic feedback supports hypothesis generation and experiment
> planning. It does not replace real-user research or predict market
> success."

## How the Platform Recommends a Real-User Follow-Up Test

Every decision memo — regardless of Proceed, Iterate, or Stop — includes a
`real_user_test` object (`RealUserTestPlan`,
`backend/app/schemas/decision_memo.py`) with exactly these fields:

- `objective` — what this specific follow-up test is meant to learn.
- `target_participants` — the real-user population that maps to the
  personas used.
- `method` — how the test will be run (e.g. moderated usability test,
  survey, A/B test).
- `sample_size_rationale` — why the proposed scope fits the next learning
  step. This must **never** claim that a specific participant count alone
  guarantees statistical validity — enforced by schema validation requiring
  the field be non-blank, and by the generation prompt instructing the
  model not to make that claim.
- `tasks_or_questions` — the concrete tasks or questions participants will
  face.
- `success_metrics` — a metric (or metrics) for *this specific test*,
  distinct from the product's overall success metric in the brief.
- `stopping_rule` — when to stop the test (e.g. after N sessions, or once a
  blocker recurs a set number of times), so the test is scoped small enough
  to run before committing to a larger build.

All list fields (`target_participants`, `tasks_or_questions`,
`success_metrics`) are normalized (trimmed, deduplicated, blanks dropped)
and required to be non-empty; all string fields are required to be
non-blank.

## Human-Feedback Comparison and the Decision Memo

The human-feedback comparison feature closes the loop: once anonymized
real-participant feedback is entered (`HumanFeedback`, gated on the
experiment being `completed` or `partially_completed`), `HumanComparisonService`
deterministically compares it against the synthetic findings — persisted
`SimulationRun`s, not `Insight`s — and records shared themes, human-only
themes, synthetic-only themes, score-direction alignment, and
task-completion-rate deltas.

This comparison is intentionally **independent of the Decision Memo**:

- A Decision Memo, once generated, is never automatically regenerated or
  altered when new `HumanFeedback` is added — `DecisionMemoService` is not
  invoked by any human-feedback operation.
- If a Decision Memo already exists when the comparison is requested,
  `HumanComparisonService` compares the memo's `created_at` timestamp
  against the latest feedback record's `created_at` and, when the memo
  predates the feedback, includes a deterministic warning in
  `data_quality_warnings` stating so. The frontend surfaces this warning
  directly rather than re-deriving the condition or silently updating the
  memo.
- The comparison never computes or implies an updated Proceed/Iterate/Stop
  recommendation, a validation score, or a claim that the synthetic
  personas were "correct." It is a factual comparison of two independent
  evidence sources, not a second decision-safety pass.

Real feedback is more decision-relevant than synthetic feedback, but a
small manually entered sample is never presented as statistically
representative:

> "Real-participant feedback entered into this platform may represent a
> small qualitative sample. The comparison supports learning; it does not
> establish statistical significance or market validation."
