# models

SQLAlchemy ORM models, registered on `Base.metadata` via this package's
`__init__.py` so Alembic autogeneration and `Base.metadata.create_all()`
both see them.

Implemented:

- `project.py` — `Project` (one product-discovery workspace and its
  product brief: name, problem statement, target user, product hypothesis,
  success metric, assumptions as a JSON list of strings, `ProjectStatus`
  enum defaulting to `draft`, UTC timestamps). Owns `evidence_items` with
  `cascade="all, delete-orphan"`.
- `evidence_item.py` — `EvidenceItem` (one text-based research item
  belonging to exactly one `Project`: `EvidenceType` enum, title, content,
  optional source label, UTC timestamps).
- `persona.py` — `Persona` (one evidence-grounded synthetic user persona
  belonging to exactly one `Project`).
- `experiment.py` — `Experiment` (a controlled two-variant simulation
  experiment: objective, hypothesis, scenario, `evaluation_criteria` as a
  JSON list, `repeat_count` 1-3, `ExperimentStatus` enum defaulting to
  `draft`, `started_at`/`completed_at`). Owns `variants` and `runs` with
  `cascade="all, delete-orphan"`, and references its selected `Persona`s
  via the `experiment_personas` association table (a plain `Table`, not a
  mapped class) so the persona set stays reproducible.
- `variant.py` — `Variant` (`VariantKey` enum `A`/`B`, name, description),
  with a `(experiment_id, key)` uniqueness constraint.
- `simulation_run.py` — `SimulationRun` (one persona x variant x repetition
  result): `SimulationRunStatus` (`completed`/`failed`), successful-run
  fields (`TaskOutcome`, 1-5 scores, structured lists, evidence
  references), safe failed-run fields (`FailureType`, a short message —
  never raw provider output), token/latency/cost metadata, and a
  uniqueness constraint on `(experiment_id, variant_id, persona_id,
  repetition_index)`.
- `insight.py` — `Insight` (one locally validated, evidence-linked
  qualitative finding clustered from an Experiment's completed runs):
  `InsightCategory`, `VariantScope`, frequency/persona counts,
  `supporting_run_ids`/`supporting_evidence_ids`, `ConfidenceLevel`
  (reused from `persona.py`). Immutable once persisted; a uniqueness
  constraint on `(experiment_id, title, category, variant_scope)`.
- `decision_memo.py` — `DecisionMemo` (one structured Proceed/Iterate/Stop
  recommendation per Experiment): `Recommendation` enum, supporting
  findings/risks/assumptions as JSON lists, a `real_user_test` JSON plan.
  Exactly one memo per Experiment (`unique=True` on `experiment_id`).
- `human_feedback.py` — `HumanFeedback` (anonymized real-participant
  feedback manually entered by the PM for one Experiment): pseudonymous
  `participant_label`, `VariantKey`/`TaskOutcome` (reused from
  `variant.py`/`simulation_run.py`), 1-5 scores, `HumanFeedbackSourceMethod`,
  optional `session_date`, normalized qualitative JSON lists. Editable and
  deletable (unlike `Insight`/`DecisionMemo`) since manually entered
  research data may need correction. No PII fields. A uniqueness
  constraint on `(experiment_id, participant_label, variant_key)`.
