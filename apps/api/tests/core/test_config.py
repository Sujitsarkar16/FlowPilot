import pytest
from pydantic import ValidationError

from app.core.config import Settings

SUPABASE_DATABASE_URL = (
    "postgresql+asyncpg://postgres:password@db.example.supabase.co:5432/postgres"
)
SUPABASE_POOLER_DATABASE_URL = (
    "postgresql+asyncpg://postgres.example:password@"
    "aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
)


@pytest.mark.parametrize("database_url", (SUPABASE_DATABASE_URL, SUPABASE_POOLER_DATABASE_URL))
def test_development_settings_accept_supabase_database_urls(database_url: str) -> None:
    settings = Settings(_env_file=None, database_url=database_url)
    assert settings.environment == "development"
    assert settings.database_url == database_url


def test_local_or_non_postgres_database_urls_are_rejected() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg"):
        Settings(_env_file=None, database_url="sqlite+aiosqlite://")


def test_production_requires_encryption() -> None:
    with pytest.raises(ValidationError, match="production requires ENCRYPTION_KEY"):
        Settings(
            _env_file=None,
            database_url=SUPABASE_DATABASE_URL,
            FLOWPILOT_ENV="production",
            supabase_url="https://project.supabase.co",
        )


def test_production_requires_supabase_auth_url() -> None:
    with pytest.raises(ValidationError, match="production requires SUPABASE_URL"):
        Settings(
            _env_file=None,
            database_url=SUPABASE_DATABASE_URL,
            FLOWPILOT_ENV="production",
            encryption_key="a" * 32,
        )
