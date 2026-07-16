import hmac
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from time import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes import mock_bank
from app.api.routes.mock_bank import router
from app.core.config import Settings
from app.core.security_headers import RequestBodyLimitMiddleware
from app.db.session import get_session
from app.models.user import User


def _signed(payload: dict[str, object], timestamp: str | None = None) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = timestamp or str(int(time()))
    signature = hmac.new(b"secret", f"{timestamp}.".encode() + body, sha256).hexdigest()
    return body, {
        "Content-Type": "application/json",
        "X-Mock-Bank-Timestamp": timestamp,
        "X-Mock-Bank-Signature": f"sha256={signature}",
    }


@pytest.mark.asyncio
async def test_signed_webhook_rejects_bad_stale_replayed_and_oversized_deliveries(
    session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mock_bank, "get_settings", lambda: Settings(mock_bank_webhook_secret="secret"))
    user = User(auth_subject="webhook-user")
    session.add(user)
    await session.commit()

    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=512)
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    payload = {
        "user_id": str(user.id), "transaction_id": "salary-webhook-1", "amount": 5000,
        "currency": "usd", "occurred_at": datetime.now(UTC).isoformat(),
    }
    body, headers = _signed(payload)
    stale_body, stale_headers = _signed(payload, "0")
    stale_headers["X-Mock-Bank-Signature"] = "sha256=" + hmac.new(
        b"secret", b"0." + stale_body, sha256
    ).hexdigest()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        valid = await client.post("/api/v1/mock-bank/salary-credits", content=body, headers=headers)
        replay = await client.post("/api/v1/mock-bank/salary-credits", content=body, headers=headers)
        wrong = await client.post(
            "/api/v1/mock-bank/salary-credits", content=body,
            headers={**headers, "X-Mock-Bank-Signature": "sha256=wrong"},
        )
        stale = await client.post("/api/v1/mock-bank/salary-credits", content=stale_body, headers=stale_headers)
        oversized = await client.post("/api/v1/mock-bank/salary-credits", content=b"x" * 513)

    assert valid.status_code == 201
    assert replay.status_code == 409
    assert wrong.status_code == stale.status_code == 401
    assert "secret" not in wrong.text.lower()
    assert oversized.status_code == 413
