import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import (
    RateLimiter,
    RateLimitExceeded,
    RateLimitMiddleware,
    RateLimitRule,
    rate_limit_bucket,
)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/plans/abc/execute",
        "/api/v1/plans/abc/promote",
        "/api/v1/plans/abc/cancel",
        "/api/v1/approvals/abc/approve",
        "/api/v1/approvals/abc/reject",
        "/api/v1/actions/abc/retry",
        "/api/v1/actions/abc/rollback",
    ],
)
def test_consequential_mutations_use_execution_bucket(path: str) -> None:
    assert rate_limit_bucket(path) == "execution"


def test_plan_reads_are_not_rate_limited() -> None:
    assert rate_limit_bucket("/api/v1/plans/abc") is None
    assert rate_limit_bucket("/api/v1/plans/abc/stream") is None


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
