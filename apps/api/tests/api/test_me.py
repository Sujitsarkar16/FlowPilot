from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_admin, get_current_user
from app.api.routes.me import router
from app.models.enums import AutonomyLevel, UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_verified_subjects_create_distinct_local_users(session: object) -> None:
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/me", "headers": []})
    first = await get_current_user(
        request,
        {"sub": "user-one", "email": "one@example.com", "user_metadata": {"name": "One"}},
        session,  # type: ignore[arg-type]
    )
    second = await get_current_user(
        request,
        {"sub": "user-two", "email": "two@example.com", "user_metadata": {"name": "Two"}},
        session,  # type: ignore[arg-type]
    )

    assert (first.auth_subject, first.email, first.display_name, first.role) == (
        "user-one",
        "one@example.com",
        "One",
        UserRole.MEMBER,
    )
    assert (second.auth_subject, second.email, second.display_name) == (
        "user-two",
        "two@example.com",
        "Two",
    )
    assert first.id != second.id
    with pytest.raises(HTTPException, match="Administrator role required"):
        await get_current_admin(first)


def test_me_returns_only_safe_profile_fields() -> None:
    app = FastAPI()
    user = User(
        id=uuid4(),
        auth_subject="user-123",
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
