"""In-memory abuse controls for sensitive API endpoints."""

import asyncio
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from time import monotonic

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import Settings


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


class RateLimitExceeded(Exception):
    def __init__(self, rule: RateLimitRule, retry_after_seconds: int) -> None:
        self.rule = rule
        self.retry_after_seconds = retry_after_seconds

    @property
    def detail(self) -> dict[str, int | str]:
        return {
            "code": "rate_limit_exceeded",
            "limit": self.rule.limit,
            "retry_after_seconds": self.retry_after_seconds,
        }


class RateLimiter:
    # ponytail: This process-local limiter is limited to one API instance; use Redis or another
    # shared atomic store before horizontal scaling.
    """Process-local sliding-window limiter."""

    def __init__(
        self, rules: dict[str, RateLimitRule], clock: Callable[[], float] = monotonic
    ) -> None:
        self.rules = rules
        self._clock = clock
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, bucket: str, identifier: str) -> None:
        rule = self.rules[bucket]
        now = self._clock()
        async with self._lock:
            hits = self._hits[(bucket, identifier)]
            while hits and hits[0] <= now - rule.window_seconds:
                hits.popleft()
            if len(hits) >= rule.limit:
                raise RateLimitExceeded(rule, max(1, ceil(rule.window_seconds - (now - hits[0]))))
            hits.append(now)


def rate_limit_bucket(path: str) -> str | None:
    if path.startswith("/api/v1/auth/"):
        return "auth"
    if path == "/api/v1/events/manual":
        return "manual"
    if path.startswith(("/api/v1/webhooks/", "/api/v1/mock-bank/")):
        return "webhook"
    if path.startswith("/api/v1/ai/") or path.endswith(("/interpret", "/plan")):
        return "ai"
    # Consequential mutations that drive real connector side effects.
    if path.startswith("/api/v1/plans/") and path.endswith(("/execute", "/promote", "/cancel")):
        return "execution"
    if path.startswith("/api/v1/approvals/") and path.endswith(("/approve", "/reject")):
        return "execution"
    if path.startswith("/api/v1/actions/") and path.endswith(("/retry", "/rollback")):
        return "execution"
    return None


def rate_limiter_from_settings(settings: Settings) -> RateLimiter:
    window = settings.rate_limit_window_seconds
    return RateLimiter(
        {
            "manual": RateLimitRule(settings.rate_limit_manual_events, window),
            "auth": RateLimitRule(settings.rate_limit_auth_requests, window),
            "webhook": RateLimitRule(settings.rate_limit_webhooks, window),
            "ai": RateLimitRule(settings.rate_limit_ai_requests, window),
            "execution": RateLimitRule(settings.rate_limit_execution_requests, window),
        }
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit sensitive routes by direct peer IP before request work begins."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        bucket = rate_limit_bucket(request.url.path)
        if bucket:
            client_ip = request.client.host if request.client else "unknown"
            try:
                await request.app.state.rate_limiter.check(bucket, f"ip:{client_ip}")
            except RateLimitExceeded as error:
                return JSONResponse(
                    status_code=429,
                    content={"detail": error.detail},
                    headers={"Retry-After": str(error.retry_after_seconds)},
                )
        return await call_next(request)
