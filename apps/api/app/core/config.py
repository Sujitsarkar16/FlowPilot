"""Typed application configuration."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=False, enable_decoding=False
    )

    environment: Literal["development", "test", "production"] = Field(
        default="development", validation_alias="FLOWPILOT_ENV"
    )
    # The application uses Supabase Postgres exclusively. Use the Supabase pooler URL for
    # application traffic and set MIGRATIONS_DATABASE_URL to the direct database URL when
    # running Alembic migrations.
    database_url: str = Field()
    migrations_database_url: str | None = None
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    cors_origins: tuple[AnyHttpUrl, ...] = ()

    auth_app_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    auth_google_client_id: str | None = None
    auth_google_client_secret: SecretStr | None = None
    auth_google_redirect_uri: AnyHttpUrl = AnyHttpUrl(
        "http://localhost:8000/api/v1/auth/google/callback"
    )
    auth_session_secret: SecretStr | None = None
    auth_state_secret: SecretStr | None = None
    auth_cookie_domain: str | None = None
    auth_cookie_name: str = "flowpilot_session"
    auth_cookie_secure: bool = False
    auth_session_lifetime_seconds: int = Field(default=2_592_000, ge=300, le=31_536_000)
    auth_google_state_lifetime_seconds: int = Field(default=600, ge=60, le=3_600)
    encryption_key: SecretStr | None = None
    encryption_previous_keys: tuple[SecretStr, ...] = ()
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_manual_events: int = Field(default=30, ge=1, le=10000)
    rate_limit_auth_requests: int = Field(default=10, ge=1, le=10000)
    rate_limit_webhooks: int = Field(default=60, ge=1, le=10000)
    rate_limit_ai_requests: int = Field(default=10, ge=1, le=10000)
    # Consequential mutations that trigger real connector side effects (execute/approve/retry).
    rate_limit_execution_requests: int = Field(default=20, ge=1, le=10000)
    request_body_limit_bytes: int = Field(default=1_048_576, ge=1024, le=52_428_800)
    event_attachment_max_bytes: int = Field(default=5_242_880, ge=1_024, le=26_214_400)
    webhook_timestamp_window_seconds: int = Field(default=300, ge=1, le=3600)
    metrics_enabled: bool = False
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: AnyHttpUrl = AnyHttpUrl(
        "http://localhost:8000/api/v1/connections/google/callback"
    )
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    github_redirect_uri: AnyHttpUrl = AnyHttpUrl(
        "http://localhost:8000/api/v1/connections/github/callback"
    )
    connection_success_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3000/dashboard/connections")
    telegram_bot_token: SecretStr | None = None
    telegram_mock_mode: bool = False
    mock_bank_webhook_secret: SecretStr | None = None
    client_availability_start_hour: int = Field(default=10, ge=0, le=23)
    client_availability_end_hour: int = Field(default=16, ge=1, le=24)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "google/gemini-2.5-flash"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value

    @field_validator("auth_cookie_domain", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("encryption_previous_keys", mode="before")
    @classmethod
    def parse_previous_keys(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(key.strip() for key in value.split(",") if key.strip())
        return value

    @field_validator("database_url", "migrations_database_url")
    @classmethod
    def validate_database_url(cls, value: str | None) -> str | None:
        """Accept any async SQLAlchemy PostgreSQL URL (Supabase, Neon, Railway, local, etc.)."""
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in ("postgresql+asyncpg", "postgres+asyncpg"):
            raise ValueError(
                "database URLs must use the postgresql+asyncpg (or postgres+asyncpg) scheme"
            )
        return value

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.client_availability_start_hour >= self.client_availability_end_hour:
            raise ValueError("client availability start must precede its end")
        if self.environment == "production":
            if not self.encryption_key:
                raise ValueError("production requires ENCRYPTION_KEY")
            if (
                self.auth_session_secret is None
                or not self.auth_session_secret.get_secret_value()
                or self.auth_state_secret is None
                or not self.auth_state_secret.get_secret_value()
            ):
                raise ValueError("production requires local authentication secrets")
            if (
                not self.auth_google_client_id
                or self.auth_google_client_secret is None
                or not self.auth_google_client_secret.get_secret_value()
            ):
                raise ValueError("production requires Google authentication credentials")
            if not self.auth_cookie_secure:
                raise ValueError("production requires AUTH_COOKIE_SECURE=true")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    # BaseSettings resolves this required value from DATABASE_URL or the local .env file.
    return Settings()  # type: ignore[call-arg]
