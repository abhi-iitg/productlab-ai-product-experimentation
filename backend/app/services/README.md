# services

Business logic that coordinates repositories, enforces not-found
behavior, and owns transaction completion (commit on success, rollback on
failure — repositories themselves never commit).

Implemented:

- `project.py` — `ProjectService`: create/list/get/update/delete for the
  product brief. Raises `app.core.exceptions.NotFoundError` for a missing
  project, translated by the API layer into a 404.
- `evidence.py` — `EvidenceService`: create/list/get/update/delete for
  evidence items, always scoped to a project. Every lookup confirms the
  evidence item belongs to the given project, so evidence from one project
  is never retrievable or editable through another project's ID.
- `persona.py` — `PersonaGenerationService`: builds the deterministic
  evidence context, calls `PersonaLLMProvider`, and persists every
  generated persona atomically in one transaction.
- `experiment.py` — `ExperimentService`: draft-only CRUD for
  `Experiment`/`Variant`, persona-selection validation, the deterministic
  30-run-limit check (`MAX_SIMULATION_RUNS`), and read-only access to
  persisted `SimulationRun`s. Rejects editing/deleting once an experiment
  is no longer `draft` (`app.core.exceptions.ConflictError`, 409). Never
  calls an LLM abstraction.
- `experiment_execution.py` — `ExperimentExecutionService`: the only place
  execution happens. Re-verifies draft status, confirmation, personas,
  variants, and the run limit; verifies provider configuration before
  flipping the experiment to `running`; then runs the Variant A/B x persona
  x repeat matrix synchronously in stable order, committing each completed
  or failed run independently (see `docs/architecture.md` for why this
  differs from persona generation's atomic-batch transaction).
- `analytics.py` — `ExperimentAnalyticsService`: deterministic aggregation
  over persisted `SimulationRun`s (coverage, per-variant metrics, theme
  counts, failure breakdown, evidence coverage, persona disagreement). No
  LLM calls, no writes.
- `insight_generation.py` — `InsightGenerationService`: builds the
  deterministic analytics context, calls `InsightLLMProvider`, validates
  every reference against the experiment's own runs/evidence, and persists
  the batch atomically. Rejects duplicate generation for an experiment.
- `decision_memo.py` — `DecisionMemoService`: requires at least one
  persisted `Insight`, recomputes analytics, calls
  `DecisionMemoLLMProvider`, applies the responsible-AI decision-safety
  rules (forbidden market-validation claims, proceed-requires-real-user-
  validation-language, data-quality gating), and persists exactly one memo
  per experiment.
- `human_feedback.py` — `HumanFeedbackService`: create/list/get/update/
  delete for anonymized real-participant feedback, scoped to a project and
  experiment. Feedback may only be *added* while the experiment is
  `completed`/`partially_completed`; editing/deleting is always allowed.
  Duplicate `(participant_label, variant_key)` entries are rejected as a
  409 conflict.
- `human_comparison.py` — `HumanComparisonService`: deterministic,
  read-only comparison of persisted `SimulationRun`s against
  `HumanFeedback` — synthetic/human per-variant aggregation, exact
  normalized theme matching, A-vs-B score-direction alignment,
  task-completion rate deltas, and data-quality warnings. No LLM calls, no
  embeddings, no writes.
