"""Settings defaults and environment-variable override tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.APP_NAME == "AI Product Experiment Platform API"
    assert settings.APP_ENV == "development"
    assert settings.APP_DEBUG is True
    assert settings.API_PREFIX == "/api/v1"
    assert settings.DATABASE_URL == "sqlite:///./data/app.db"
    assert settings.CORS_ORIGINS == ["http://localhost:3000"]
    assert settings.LOG_LEVEL == "INFO"


def test_environment_variable_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Custom Service Name")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/custom.db")

    settings = Settings(_env_file=None)

    assert settings.APP_NAME == "Custom Service Name"
    assert settings.APP_ENV == "test"
    assert settings.APP_DEBUG is False
    assert settings.DATABASE_URL == "sqlite:///./data/custom.db"


def test_cors_origins_parsed_from_comma_separated_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://example.com")

    settings = Settings(_env_file=None)

    assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()

    assert first is second


def test_e2e_fake_ai_defaults_false() -> None:
    settings = Settings(_env_file=None)

    assert settings.E2E_FAKE_AI is False


def test_e2e_fake_ai_allowed_when_app_env_test() -> None:
    settings = Settings(_env_file=None, APP_ENV="test", E2E_FAKE_AI=True)

    assert settings.E2E_FAKE_AI is True
    assert settings.APP_ENV == "test"


@pytest.mark.parametrize("app_env", ["development", "production", "staging"])
def test_e2e_fake_ai_rejected_outside_test_env(app_env: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV=app_env, E2E_FAKE_AI=True)
