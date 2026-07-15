import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_settings_have_safe_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.environment == "development"
    assert settings.database_url.startswith("postgresql+asyncpg")


def test_production_requires_auth_and_encryption() -> None:
    with pytest.raises(ValidationError, match="production requires"):
        Settings(_env_file=None, FLOWPILOT_ENV="production")
