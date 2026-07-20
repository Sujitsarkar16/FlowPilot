import pytest
from pydantic import ValidationError

from app.core.config import Settings

DATABASE_URL = "postgresql+asyncpg://postgres:password@db.example.test:5432/flowpilot"


def test_development_settings_accept_postgres_asyncpg_urls() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL)
    assert settings.environment == "development"
    assert settings.database_url == DATABASE_URL


def test_local_or_non_postgres_database_urls_are_rejected() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg"):
        Settings(_env_file=None, database_url="sqlite+aiosqlite://")


def test_production_requires_encryption() -> None:
    with pytest.raises(ValidationError, match="production requires ENCRYPTION_KEY"):
        Settings(_env_file=None, database_url=DATABASE_URL, FLOWPILOT_ENV="production")


def test_production_requires_local_authentication_secrets() -> None:
    with pytest.raises(ValidationError, match="local authentication secrets"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            FLOWPILOT_ENV="production",
            encryption_key="encryption-key",
        )


def test_production_requires_google_and_secure_cookies() -> None:
    with pytest.raises(ValidationError, match="Google authentication credentials"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            FLOWPILOT_ENV="production",
            encryption_key="encryption-key",
            auth_session_secret="session-secret",
            auth_state_secret="state-secret",
        )
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            FLOWPILOT_ENV="production",
            encryption_key="encryption-key",
            auth_session_secret="session-secret",
            auth_state_secret="state-secret",
            auth_google_client_id="google-client",
            auth_google_client_secret="google-secret",
        )


def test_empty_cookie_domain_is_treated_as_host_only() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL, auth_cookie_domain="")
    assert settings.auth_cookie_domain is None
