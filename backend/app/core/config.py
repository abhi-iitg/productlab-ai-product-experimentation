"""Application configuration loaded from environment variables."""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the FastAPI application.

    Values are sourced from environment variables (or a local `.env` file)
    with sensible local-development defaults. Nothing here is a real secret.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ProductLab-AI Product Experimentation API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_VERSION: str = "0.1.0"

    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./data/app.db"

    # NoDecode: skip pydantic-settings' default JSON-decoding of complex-typed
    # env vars, so the raw comma-separated string reaches the validator below.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    LOG_LEVEL: str = "INFO"

    # OpenAI provider abstraction (Stage 4: persona generation). The
    # application must start and all non-AI routes must work with no key
    # configured; only calling the persona-generation endpoint requires it.
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Optional, user-configured provider pricing (Stage 5: simulation cost
    # estimation). Prices change over time and are never hardcoded; when
    # either is unset, estimated_cost_usd is left null rather than guessed.
    OPENAI_INPUT_COST_PER_1M: Decimal | None = None
    OPENAI_OUTPUT_COST_PER_1M: Decimal | None = None

    # Test-only switch (Stage 9A) that makes the four LLM-calling services
    # use deterministic in-process fake providers instead of OpenAI, so
    # Playwright can exercise the real FastAPI app end-to-end with no
    # network access and no API key. Only ever honored when APP_ENV=test;
    # see `_validate_e2e_fake_ai_requires_test_env` below.
    E2E_FAKE_AI: bool = False

    @model_validator(mode="after")
    def _validate_e2e_fake_ai_requires_test_env(self) -> "Settings":
        if self.E2E_FAKE_AI and self.APP_ENV != "test":
            raise ValueError(
                "E2E_FAKE_AI=true is only permitted when APP_ENV=test. Refusing to "
                "start with fake AI providers outside the test environment."
            )
        return self

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be set as a comma-separated string in env vars."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("OPENAI_INPUT_COST_PER_1M", "OPENAI_OUTPUT_COST_PER_1M")
    @classmethod
    def _validate_non_negative_cost(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("must be non-negative")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Tests that need different configuration (e.g. a different DATABASE_URL)
    should call `get_settings.cache_clear()` after setting environment
    variables, or override the `get_settings` FastAPI dependency directly.
    """
    return Settings()
