import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimiter, RateLimitExceeded, RateLimitMiddleware, RateLimitRule


@pytest.mark.asyncio
async def test_rate_limiter_rejects_repeated_calls_with_retry_information() -> None:
    def clock() -> float:
        return 10.25

    limiter = RateLimiter({"manual": RateLimitRule(limit=1, window_seconds=60)}, clock)
    await limiter.check("manual", "user:trusted-subject")
    with pytest.raises(RateLimitExceeded) as error:
        await limiter.check("manual", "user:trusted-subject")
    assert error.value.detail["code"] == "rate_limit_exceeded"
    assert error.value.retry_after_seconds == 60


def test_rate_limit_middleware_returns_structured_429() -> None:
    app = FastAPI()
    app.state.rate_limiter = RateLimiter({"manual": RateLimitRule(limit=1, window_seconds=60)})
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/events/manual")
    async def manual_event() -> dict[str, bool]:
        return {"accepted": True}

    client = TestClient(app)
    assert client.post("/api/v1/events/manual").status_code == 200
    response = client.post("/api/v1/events/manual")
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "rate_limit_exceeded"
    assert response.headers["Retry-After"] == "60"
