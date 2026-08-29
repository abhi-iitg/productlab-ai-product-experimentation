# schemas

Pydantic schemas for API request/response validation. Every schema trims
incoming strings, rejects blank required text, and rejects an empty PATCH
body. Read schemas use `from_attributes=True` so they can validate directly
off ORM model instances without exposing internal SQLAlchemy state.

Implemented:

- `project.py` — `ProjectCreate`, `ProjectUpdate`, `ProjectRead`. Also
  normalizes `assumptions`: trims each entry, drops blanks, and removes
  duplicates (case-insensitive).
- `evidence.py` — `EvidenceItemCreate`, `EvidenceItemUpdate`,
  `EvidenceItemRead`. Validates `evidence_type` against the supported
  enum values.
- `persona.py` — `PersonaGenerateRequest`/`PersonaRead` (API-facing), plus
  `PersonaGenerationResult`/`GeneratedPersona`/`EvidenceReference` which
  validate the *raw, untrusted* LLM output before anything is persisted —
  evidence references are checked against the evidence actually supplied
  in the generation context via Pydantic validation `context`.
- `experiment.py` — `ExperimentCreate`/`ExperimentUpdate`/`ExperimentRead`,
  `VariantCreate`/`VariantRead`, `ExperimentExecuteRequest` (requires
  `confirm_execution: true`), `ExperimentExecutionSummary`. Validates
  exactly one Variant A and one Variant B, normalizes/deduplicates
  `evaluation_criteria`, and rejects an empty PATCH body.
- `simulation_run.py` — `SimulationOutput`, which validates the *raw,
  untrusted* simulation LLM output the same way `PersonaGenerationResult`
  does (reusing `EvidenceReference`, checked against the evidence IDs the
  specific persona being simulated is grounded in); `SimulationCallResult`
  wraps it with non-negative token/latency metadata; `SimulationRunRead` is
  the API-facing read schema.
- `analytics.py` — `AnalyticsResponse` and its nested schemas
  (`VariantMetrics`, `ThemeCounts`, `DataQualityFlags`, etc.) for the
  deterministic `GET .../analysis` response.
- `insight.py` — `InsightCandidate`/`InsightGenerationResult` (raw,
  untrusted LLM output, validated against the experiment's own completed
  runs and cited evidence via Pydantic `context`), `InsightRead`.
- `decision_memo.py` — `DecisionMemoCandidate` (raw, untrusted LLM output,
  including the `RealUserTestPlan` sub-schema), `DecisionMemoRead`.
- `human_feedback.py` — `HumanFeedbackCreate`/`HumanFeedbackUpdate`/
  `HumanFeedbackRead`. Plain CRUD schemas (no LLM output boundary): trims
  `participant_label`/`feedback_summary`, validates 1-5 scores, normalizes
  the five qualitative list fields (trim, drop blanks, dedupe
  case-insensitive), and rejects an empty PATCH body.
- `human_comparison.py` — `HumanComparisonResponse` and its nested
  comparison schemas for the deterministic real-vs-synthetic comparison.
  Reuses `analytics.TaskOutcomeDistribution`. No schema here is derived
  from untrusted LLM output.
