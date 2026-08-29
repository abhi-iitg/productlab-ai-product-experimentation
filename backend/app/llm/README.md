# llm

Two independent provider abstractions live here: persona generation
(Stage 4, called only by `PersonaGenerationService`) and simulation
execution (Stage 5, called only by `ExperimentExecutionService`). No route
function or repository calls either directly.

## Persona generation (Stage 4)

- `provider.py` — `PersonaLLMProvider`, the typed `Protocol` the service
  depends on. Production code and tests both satisfy this interface;
  neither the service nor the routes import the OpenAI SDK directly.
- `openai_provider.py` — `OpenAIPersonaProvider`, the real implementation.
  Reads `OPENAI_API_KEY`/`OPENAI_MODEL` from settings, initializes the
  OpenAI client lazily (constructing the provider never requires an API
  key — only calling `generate_personas` does), calls the Responses API
  with `text.format.type = "json_object"`, then locally `json.loads`s and
  Pydantic-validates the output before returning it. No streaming.
- `prompts.py` — `PERSONA_PROMPT_VERSION` and the stable system
  instructions, kept separate from the project/evidence context and from
  user-controlled `focus` text.
- `context.py` — the deterministic project+evidence context builder and
  its character limit (`PERSONA_CONTEXT_CHAR_LIMIT`).

## Simulation execution (Stage 5)

- `simulation_provider.py` — `SimulationLLMProvider`, a separate typed
  `Protocol` (not shared with `PersonaLLMProvider`, so the two remain
  independently swappable/testable). Adds `ensure_configured()`, called
  once before an experiment's status flips to `running` so a missing API
  key is caught before any run is dispatched, rather than surfacing as N
  individual per-run failures.
- `openai_simulation_provider.py` — `OpenAISimulationProvider`, the real
  implementation. Same lazy-client, Responses API, local
  `json.loads`-then-Pydantic-validate pattern as the persona provider, plus:
  measures latency with a monotonic clock, captures token usage when the
  provider reports it, and distinguishes malformed JSON from schema-invalid
  output from an evidence-reference-specific validation failure (inspecting
  the Pydantic `ValidationError`'s error locations) so
  `SimulationRun.failure_type` records the precise safe category.
- `simulation_prompts.py` — `SIMULATION_PROMPT_VERSION` and the stable
  system instructions (evaluate only the supplied variant, respond from the
  bounded persona perspective, cite only supplied evidence IDs, never claim
  market validation).
- `simulation_context.py` — the deterministic per-run context builder
  (project + experiment + the single *active* variant + persona + only the
  evidence that persona's own references cite) and its character limit
  (`SIMULATION_CONTEXT_CHAR_LIMIT`). The competing variant is never
  included, so the model is never steered toward a comparative preference.

## Shared

- `exceptions.py` — typed provider failures shared by both abstractions
  (`LLMConfigurationError`, `LLMTimeoutError`, `LLMRateLimitError`,
  `LLMStatusError`, `LLMEmptyOutputError`, `LLMInvalidOutputError`, plus
  `LLMMalformedJSONError`/`LLMInvalidSchemaError`/
  `LLMInvalidEvidenceReferenceError` used only by the simulation provider,
  which — unlike persona generation — must distinguish these for
  `SimulationRun.failure_type`). Services catch these and translate them
  into the safe, generic `app.core.exceptions` errors the API returns —
  provider internals never reach a client.

No vector database, no embeddings, no retrieval service, no web access in
either abstraction — every fact comes from the project's own persisted
rows. Automated tests never import either `openai_*_provider.py`'s
`OpenAI` client or make network calls — they inject a deterministic fake
satisfying the relevant `Protocol` instead (see `backend/tests/fakes.py`).
