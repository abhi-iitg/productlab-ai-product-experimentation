# tests

Pytest suite covering:

- **Stage 2 foundation** — application factory, health endpoint/schema,
  request ID middleware, centralized error handling, settings
  defaults/overrides, SQLite engine/session behavior, Alembic
  configuration importability.
- **Stage 3 domain** — `Project`/`EvidenceItem` model behavior (defaults,
  UTC timestamps, relationships, cascade delete), Pydantic schema
  validation, repository persistence behavior, service-layer not-found and
  transaction (commit/rollback) behavior, the full Project and Evidence
  API surface (including cross-project evidence isolation), and the real
  Alembic migration's upgrade/downgrade/upgrade cycle.
- **Stage 4 personas** — `Persona` model behavior, the raw-LLM-output vs.
  API-facing schema validation boundary (including evidence-reference
  verification against the generation context), the deterministic
  persona-context builder, `PersonaGenerationService` (atomic batch
  persistence, provider-error translation), the generate/list/get/delete
  API, and `OpenAIPersonaProvider`'s lazy-client/safe-failure behavior —
  via `FakePersonaProvider` (`fakes.py`), never a live OpenAI call.
- **Stage 5 experiments** — `Experiment`/`Variant`/`SimulationRun` model
  behavior (uniqueness constraints, cascade delete), the Experiment/Variant
  request schemas and the raw-LLM-output `SimulationOutput` schema, the
  deterministic per-run simulation-context builder (active variant only,
  persona-referenced evidence only), `ExperimentService` (draft-only CRUD,
  the 30-run limit), `ExperimentExecutionService` (stable run-matrix
  ordering, every documented failure category, mixed-outcome final status,
  independent per-run commits, token/latency/cost persistence), the full
  Experiment/run API surface, and `OpenAISimulationProvider`'s
  lazy-client/safe-failure behavior — via `FakeSimulationProvider`
  (`fakes.py`), never a live OpenAI call. `experiment_helpers.py` centralizes
  the deeper Project+EvidenceItem+Persona object graph these tests need.

All tests run against an isolated temporary SQLite database (created via
the `client`/`db_session` fixtures in `conftest.py`) and make no network
calls. Every LLM abstraction is always mocked/stubbed here — no live
OpenAI calls in automated tests.
