from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_dependencies
from app.api.dependencies.auth import get_current_admin, get_current_user
from app.api.routes.me import router
from app.core.config import Settings
from app.models.enums import AutonomyLevel, UserRole
from app.models.user import User
from app.models.user_session import UserSession
from app.services.local_auth import hash_session_token


@pytest.mark.asyncio
async def test_distinct_local_sessions_resolve_to_distinct_users(session, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://postgres:password@db.example.test:5432/flowpilot",
        auth_session_secret="session-secret",
    )
    monkeypatch.setattr(auth_dependencies, "get_settings", lambda: settings)
    first = User(auth_subject="local:first", email="one@example.com")
    second = User(auth_subject="google:second", email="two@example.com", google_subject="second")
    session.add_all([first, second])
    await session.flush()
    first_token, second_token = "first-session", "second-session"
    session.add_all(
        [
            UserSession(
                user_id=first.id,
                token_hash=hash_session_token(first_token, settings),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            UserSession(
                user_id=second.id,
                token_hash=hash_session_token(second_token, settings),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        ]
    )
    await session.commit()

    first_request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/me",
            "headers": [(b"cookie", b"flowpilot_session=first-session")],
        }
    )
    second_request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/me",
            "headers": [(b"cookie", b"flowpilot_session=second-session")],
        }
    )
    assert await get_current_user(first_request, session) is first
    assert await get_current_user(second_request, session) is second
    with pytest.raises(HTTPException, match="Administrator role required"):
        await get_current_admin(first)


def test_me_returns_only_safe_profile_fields() -> None:
    app = FastAPI()
    user = User(
        id=uuid4(),
        auth_subject="local:user-123",
        email="person@example.com",
        display_name="Person",
        role=UserRole.MEMBER,
        default_autonomy=AutonomyLevel.SUGGEST,
    )

    async def current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = current_user
    app.include_router(router)
    response = TestClient(app).get("/api/v1/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": "person@example.com",
        "display_name": "Person",
        "role": "member",
        "default_autonomy": "suggest",
    }
