# core

Cross-cutting application setup.

- `config.py` — `Settings` (Pydantic Settings) loaded from environment
  variables / `.env`, with a cached `get_settings()` accessor. Includes
  optional, user-configured `OPENAI_INPUT_COST_PER_1M` /
  `OPENAI_OUTPUT_COST_PER_1M` (non-negative `Decimal`s) used only for
  simulation-run cost estimation — provider prices are never hardcoded.
- `logging.py` — `configure_logging()`, applies `LOG_LEVEL` from settings.
- `exceptions.py` — centralized handler for unexpected exceptions (returns
  a safe, generic error response instead of leaking internal details), plus
  the typed domain exceptions every service raises: `NotFoundError` (404),
  `InvalidRequestError` (422), `ConflictError` (409 — editing/deleting a
  non-draft experiment, a second execution attempt),
  `ProviderConfigurationError` (503), `ProviderError` (502).
