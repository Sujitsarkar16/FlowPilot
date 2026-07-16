"""Typed application configuration."""

from functools import lru_cache
from typing import Literal

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
    database_url: str = "postgresql+asyncpg://flowpilot:flowpilot@localhost:5432/flowpilot"
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    cors_origins: tuple[AnyHttpUrl, ...] = ()
    auth0_domain: str | None = None
    auth0_audience: str | None = None
    encryption_key: SecretStr | None = None
    encryption_previous_keys: tuple[SecretStr, ...] = ()
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_manual_events: int = Field(default=30, ge=1, le=10000)
    rate_limit_webhooks: int = Field(default=60, ge=1, le=10000)
    rate_limit_ai_requests: int = Field(default=10, ge=1, le=10000)
    request_body_limit_bytes: int = Field(default=1_048_576, ge=1024, le=52_428_800)
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

    @field_validator("encryption_previous_keys", mode="before")
    @classmethod
    def parse_previous_keys(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(key.strip() for key in value.split(",") if key.strip())
        return value

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.client_availability_start_hour >= self.client_availability_end_hour:
            raise ValueError("client availability start must precede its end")
        if self.environment == "production":
            required = (self.auth0_domain, self.auth0_audience, self.encryption_key)
            if not all(required):
                raise ValueError("production requires Auth0 settings and ENCRYPTION_KEY")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()
