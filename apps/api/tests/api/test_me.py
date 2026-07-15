from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_dependencies
from app.api.dependencies.auth import get_current_user
from app.api.routes.me import router
from app.core.auth import AuthClaims
from app.models.enums import AutonomyLevel
from app.models.user import User


class VerifiedClaims:
    async def verify(self, token: str) -> AuthClaims:
        assert token == "verified-token"
        return AuthClaims("trusted-subject", "new@example.com", "Trusted User")


@pytest.mark.asyncio
async def test_verified_subject_creates_the_local_user(
    session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth_dependencies, "get_jwt_verifier", lambda: VerifiedClaims())
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/me", "headers": []})
    user = await get_current_user(
        request,
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="verified-token"),
        session,  # type: ignore[arg-type]
    )
    assert (user.auth_subject, user.email, user.display_name) == (
        "trusted-subject",
        "new@example.com",
        "Trusted User",
    )


def test_me_returns_only_safe_profile_fields() -> None:
    app = FastAPI()
    user = User(
        id=uuid4(),
        auth_subject="trusted-subject",
        email="person@example.com",
        display_name="Person",
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
        "default_autonomy": "suggest",
    }
