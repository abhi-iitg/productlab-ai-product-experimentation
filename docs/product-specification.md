# Product Specification

This document describes the locked product specification for the MVP.
Every item in the Detailed MVP Scope section below is implemented
end-to-end; see `README.md` for the current feature summary and
`docs/architecture.md` for how each is built.

## Problem

Product teams frequently decide whether to pursue a product concept based on
unstructured intuition, a small number of informal customer conversations,
or only after committing substantial engineering effort to a full build.
Existing qualitative evidence (interviews, support tickets, reviews, prior
research) is often collected but not systematically used to stress-test a
new product hypothesis before real users are recruited for testing. There is
no lightweight, structured step between "an idea on a whiteboard" and "a
live experiment with real users."

## Target User

Early-stage product managers, product-minded founders, and UX researchers
who have some qualitative evidence about their target user already (from
past interviews, support tickets, reviews, or research notes) and are
comparing two possible product directions before investing further
engineering or research effort.

## User Need

Before running a costly and slow real-user experiment, the target user needs
a fast, structured way to: organize the evidence they already have, generate
a defensible set of personas grounded in that evidence, compare two concept
variants against those personas, and identify the specific weak assumptions
and risks that a real-user test should target next.

## Product Hypothesis

If product teams can compare concept variants against evidence-grounded
synthetic personas in a structured, repeatable way, they will identify
weaker assumptions and design more targeted real-user experiments earlier,
without mistaking synthetic feedback for market validation.

## Value Proposition

The platform turns evidence a team already has into a structured comparison
of product directions, producing a decision memo that names the weakest
assumptions and recommends a specific, small real-user experiment — instead
of leaving evidence underused and assumptions untested until after a full
build.

## Jobs To Be Done

- When I have two possible product directions and existing qualitative
  evidence, help me compare them in a structured way so I can decide which
  is worth testing with real users first.
- When I'm about to design a user research study, help me identify which of
  my assumptions are weakest so I can target the study more precisely.
- When I get synthetic feedback, help me clearly see what is evidence-backed
  versus speculative, so I don't over-trust an AI-generated result.
- When I later run a real-user test, help me compare what real users said
  against what the synthetic experiment surfaced, so I can see agreement and
  gaps — without treating similarity as proof of predictive validity.

## Primary Workflow

```
Product brief
  → research evidence
  → evidence-grounded personas
  → Product Variant A and Product Variant B
  → repeated structured simulations
  → comparative analytics
  → uncertainty and unsupported-finding analysis
  → Proceed / Iterate / Stop decision memo
  → recommended real-user experiment
```

A project owner starts by authoring a product brief and populating an
evidence library. The platform generates personas strictly grounded in that
evidence, with unsupported attributes explicitly flagged. The owner then
configures two product variants tested against a shared scenario, using the
same personas, for a configurable number of repeats, and explicitly confirms
before execution. Each simulation run produces structured, schema-validated
results. The Analytics Service aggregates these into a comparison dashboard,
and the Recommendation Service produces a Proceed/Iterate/Stop decision memo
that always includes a recommended real-user experiment. Once that real-user
experiment is run, its results can be entered and compared against the
synthetic findings.

## Detailed MVP Scope

### 1. Product Brief
Captures: product name, problem statement, target user, product hypothesis,
success metric, and assumptions. Scoped to a single project. Each project
also tracks a workspace status (`draft`, `active`, or `archived`,
defaulting to `draft`) reflecting where the project stands in the
workflow above, distinct from any per-experiment decision outcome.

### 2. Evidence Library
Text-based evidence only for the MVP: interview notes, survey responses,
support tickets, product reviews, and research notes. Each evidence item is
associated with a project and is the sole grounding source for personas
generated from that project.

### 3. Evidence-Grounded Personas
Each persona records: a name or label, goals, pain points, constraints,
behaviors, references to the specific evidence items it draws from, an
explicit confidence level, and an explicit list of unsupported assumptions
(attributes not directly traceable to evidence but included for
completeness).

### 4. Variant Experiment
An experiment defines Product Variant A and Product Variant B, a shared task
or interview scenario, and uses the same set of personas for both variants
so comparisons are apples-to-apples. The repeat count (how many times each
persona is simulated per variant, 1-3) is configurable. Execution requires
an explicit confirmation step before any simulation runs are dispatched. To
keep cost and latency bounded and predictable, the platform enforces a
deterministic maximum of 30 total simulation runs per experiment (selected
personas x 2 variants x repeat count); an experiment that would exceed this
is rejected outright rather than silently reducing the persona selection or
repeat count.

### 5. Structured Simulation Results
Each simulation run produces a structured result recording: task completion,
clarity, perceived value, adoption intent, objections, confusion, feature
requests, uncertainty, references to the evidence that grounded the
persona's response, and — when applicable — model/provider failure
information (e.g., timeout, malformed output, validation failure).

### 6. Comparison Dashboard
Aggregates simulation results across both variants: variant-level results,
where personas disagree across variants, recurring themes, task completion
rates, confusion rates, objections, findings flagged as unsupported, token
usage, estimated cost, latency, and a failure explorer for provider or
validation failures. Implementation splits this into two layers: a
deterministic `ExperimentAnalyticsService` (no LLM calls — coverage,
per-variant metrics, verbatim theme *counts*, evidence coverage, failure
breakdown, and persona disagreement), and a separate LLM-assisted Insight
generation step that clusters those verbatim counts into a small set of
named, evidence-linked findings. "Findings flagged as unsupported" is
implemented as each Insight's `confidence_level` and a dedicated
`uncertainty` category, rather than a single boolean flag.

### 7. Decision Memo
Produces a Proceed / Iterate / Stop recommendation, the supporting findings
behind it, the weakest assumptions identified, recommended product changes,
risks, uncertain conclusions, a proposed real-user experiment, and
recommended success metrics for that follow-up experiment. See
`docs/decision-framework.md` for how the recommendation is derived,
including the deterministic decision-safety rules `DecisionMemoService`
enforces after every provider response.

### 8. Human-Feedback Comparison
Allows a PM to manually enter anonymized real-participant feedback per
experiment (once it is `completed` or `partially_completed`), and
deterministically compares it against the synthetic findings from
persisted `SimulationRun`s: shared themes, human-only themes,
synthetic-only themes, A-vs-B score-direction agreement, task-completion-
rate deltas, and data-quality warnings.

**Privacy.** Only anonymized feedback is requested — no names, emails,
phone numbers, account identifiers, or demographic data. Use a
pseudonymous participant label (e.g. "Participant 1", "Interview P3",
"Tester B-02"). The platform performs no automatic PII detection; a
standing reminder is shown instead.

**Qualitative-sample limitation.** Real feedback is more decision-relevant
than synthetic feedback, but a small manually entered sample is never
presented as statistically representative — no statistical-significance
testing, confidence intervals, or predictive-accuracy claims are computed
or shown anywhere in this feature.

**Deterministic, not AI-assisted.** The comparison (`HumanComparisonService`)
makes no LLM calls, no embeddings calls, and no writes. Theme matching is
exact (trim, collapse internal whitespace, case-fold) — intentionally
conservative, since differently worded but related ideas are treated as
distinct themes rather than fuzzily merged.

**Decision Memo independence.** A Decision Memo is never automatically
regenerated when new real feedback is added. If one already exists, the
comparison surfaces a deterministic warning stating it predates the
feedback and was not automatically updated.

## Non-Goals

- Not a replacement for real-user research.
- Not a participant recruiting or research-panel management platform.
- No authentication or multi-tenant support in the MVP.
- No production-scale infrastructure (PostgreSQL, Redis, Celery,
  Kubernetes) in the MVP.
- No multi-provider LLM routing or model comparison in the MVP.
- No file parsing beyond plain-text evidence (no PDF, audio, or image
  parsing) in the MVP.
- No vector database or semantic search in the MVP.
- Not a tool for designing or fielding the real-user experiment itself — it
  recommends what to test, not how to run participant recruitment or
  survey logistics.

## Product Risks

- Users treating synthetic persona output as market truth rather than a
  hypothesis-generation aid.
- Confirmation bias when synthetic results happen to agree with the
  product owner's existing priors.
- A thin or biased evidence library producing weak, unrepresentative
  personas.
- Users skipping the recommended real-user experiment and treating the
  decision memo as final.

## AI-Specific Risks

- Hallucinated persona attributes not actually grounded in the submitted
  evidence.
- Model overconfidence — stating conclusions without appropriate
  uncertainty.
- Structured-output schema drift or malformed JSON breaking downstream
  persistence if not caught at the validation boundary.
- Provider failures (timeouts, rate limits) during simulation runs.
- Prompt or ordering sensitivity introducing bias into the Variant A vs.
  Variant B comparison.
- Uncontrolled repeat counts causing unexpected token cost or latency.

## Success Metrics

These describe how the platform itself (as a product and portfolio
artifact) will be evaluated, not a real-world go-to-market metric:

- Time from a completed product brief and evidence library to a generated
  decision memo.
- Clarity and actionability of the decision memo — whether it names a
  specific, small, executable real-user experiment.
- Accuracy of unsupported-finding flagging — whether ungrounded claims are
  reliably separated from evidence-grounded ones.
- Once human feedback is entered, the rate of agreement/divergence tracked
  between synthetic and real findings, as a measure of what the synthetic
  step is (and isn't) good for.

## Acceptance Criteria

The MVP is considered feature-complete when:

- A product brief can be authored and persisted with all required fields.
- Evidence items can be added to a project's evidence library.
- Personas are generated only from submitted evidence, each recording
  evidence references, a confidence level, and explicit unsupported
  assumptions.
- Two variants can be run against the same personas and a shared scenario,
  for a configurable repeat count, only after explicit user confirmation.
- Structured simulation results are validated locally against a Pydantic
  schema before persistence; provider or validation failures are recorded
  as explicit, visible failure data rather than dropped silently.
- The comparison dashboard surfaces token usage, estimated cost, latency,
  and failures alongside qualitative comparison results.
- The decision memo always includes a recommended real-user experiment and
  never states or implies that synthetic results predict market success.
- Human feedback can be entered and compared against synthetic findings,
  producing overlapping, human-only, and synthetic-only/unsupported themes.

## Future Extensions

Explicitly out of scope for the MVP, documented here as possible future
directions rather than committed work:

- Authentication and multi-user workspaces.
- PostgreSQL and asynchronous execution for scale.
- A background task queue (e.g., Celery with Redis) for long-running
  simulation batches.
- Support for multiple LLM providers and cross-provider comparison.
- A vector database for semantic evidence retrieval.
- File parsing beyond plain text (PDF, audio transcripts, images).
- Observability/tracing integrations (e.g., Langfuse, Sentry).
- Enterprise integrations (SSO, ticketing systems, CRM connectors).
- Kubernetes-based deployment.
