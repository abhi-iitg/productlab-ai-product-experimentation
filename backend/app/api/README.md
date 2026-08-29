# api

FastAPI routers. `router.py` assembles the top-level `api_router`, mounted
under the configured `API_PREFIX` in `app.main.create_app()`.

Implemented:

- `routes/health.py` — `GET /health`, returns a validated
  `HealthResponse` (status, service, environment, version).
- `routes/projects.py` — `POST/GET /projects`,
  `GET/PATCH/DELETE /projects/{project_id}`. Thin routes that delegate to
  `ProjectService`.
- `routes/evidence.py` — `POST/GET /projects/{project_id}/evidence`,
  `GET/PATCH/DELETE /projects/{project_id}/evidence/{evidence_id}`. Thin
  routes that delegate to `EvidenceService`.
- `routes/personas.py` — `POST /projects/{project_id}/personas/generate`,
  `GET /projects/{project_id}/personas`,
  `GET/DELETE /projects/{project_id}/personas/{persona_id}`. Thin routes
  that delegate to `PersonaGenerationService`.
- `routes/experiments.py` —
  `POST/GET /projects/{project_id}/experiments`,
  `GET/PATCH/DELETE /projects/{project_id}/experiments/{experiment_id}`,
  `POST /projects/{project_id}/experiments/{experiment_id}/execute`,
  `GET /projects/{project_id}/experiments/{experiment_id}/runs`,
  `GET /projects/{project_id}/experiments/{experiment_id}/runs/{run_id}`.
  CRUD and run-listing routes delegate to `ExperimentService`; `execute`
  delegates to `ExperimentExecutionService` (a separate FastAPI dependency,
  since it alone needs a `SimulationLLMProvider`).
- `routes/analysis.py` —
  `GET /projects/{project_id}/experiments/{experiment_id}/analysis`,
  `POST/GET .../insights/generate` and `.../insights`,
  `POST/GET .../decision-memo/generate` and `.../decision-memo`. Delegate
  to `ExperimentAnalyticsService`, `InsightGenerationService`, and
  `DecisionMemoService` respectively.
- `routes/human_feedback.py` —
  `POST/GET .../human-feedback`,
  `GET/PATCH/DELETE .../human-feedback/{feedback_id}`,
  `GET .../human-feedback/comparison`. CRUD delegates to
  `HumanFeedbackService`; the comparison route delegates to the fully
  deterministic `HumanComparisonService` (no LLM calls). The static
  `/comparison` route is declared before the dynamic `/{feedback_id}`
  route so it is never shadowed.
