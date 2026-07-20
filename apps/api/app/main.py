"""FlowPilot API application entry point."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import PlainTextResponse, Response

from app.api.routes.actions import router as actions_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.auth import router as auth_router
from app.api.routes.connections import router as connections_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.events import router as events_router
from app.api.routes.github_oauth import router as github_oauth_router
from app.api.routes.google_oauth import router as google_oauth_router
from app.api.routes.me import router as me_router
from app.api.routes.mock_bank import router as mock_bank_router
from app.api.routes.plans import execution_router
from app.api.routes.plans import router as plans_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.standing_orders import router as standing_orders_router
from app.api.routes.telegram_connection import router as telegram_connection_router
from app.core.config import get_settings
from app.core.logging import configure_logging, request_id_context, route_context
from app.core.metrics import metrics
from app.core.rate_limit import RateLimitMiddleware, rate_limiter_from_settings
from app.core.security_headers import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from app.db.session import dispose_engine, get_session_factory
from app.workers.gmail_poll_worker import GmailPollWorker
from app.workers.main import DurableWorker

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to every response and structured log entry."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        request_token = request_id_context.set(request_id)
        route_token = route_context.set(request.url.path)
        started = perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request completed", extra={"duration_ms": (perf_counter() - started) * 1000}
            )
            return response
        finally:
            request_id_context.reset(request_token)
            route_context.reset(route_token)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Set up logging, optional embedded workers, and pooled resources."""
    configure_logging()
    settings = get_settings()
    app.state.settings = settings
    workers: tuple[DurableWorker | GmailPollWorker, ...] = ()
    worker_tasks: tuple[asyncio.Task[None], ...] = ()
    if settings.embedded_workers:
        # ponytail: Render Free sleeps idle web services; move workers to dedicated services for 24/7 jobs.
        workers = (DurableWorker(get_session_factory()), GmailPollWorker(get_session_factory()))
        worker_tasks = tuple(
            asyncio.create_task(worker.run(), name=worker.worker_id) for worker in workers
        )
        logger.warning("starting workers in the API process")
    try:
        yield
    finally:
        for worker in workers:
            worker.stop()
        for task in worker_tasks:
            task.cancel()
        if worker_tasks:
            await asyncio.gather(*worker_tasks, return_exceptions=True)
        await dispose_engine()


def create_app() -> FastAPI:
    """Create the API without forcing a database connection during liveness checks."""
    settings = get_settings()
    api = FastAPI(title="FlowPilot API", version="0.2.0", lifespan=lifespan)
    api.state.rate_limiter = rate_limiter_from_settings(settings)
    api.add_middleware(RequestContextMiddleware)
    api.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=settings.request_body_limit_bytes,
        attachment_max_bytes=max(
            settings.request_body_limit_bytes,
            settings.event_attachment_max_bytes * 4 // 3 + 65_536,
        ),
    )
    api.add_middleware(RateLimitMiddleware)
    api.add_middleware(SecurityHeadersMiddleware, production=settings.environment == "production")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    api.include_router(auth_router)
    api.include_router(me_router)
    api.include_router(events_router)
    api.include_router(mock_bank_router)
    api.include_router(approvals_router)
    api.include_router(dashboard_router)
    api.include_router(plans_router)
    api.include_router(execution_router)
    api.include_router(preferences_router)
    api.include_router(actions_router)
    api.include_router(standing_orders_router)
    api.include_router(connections_router)
    api.include_router(google_oauth_router)
    api.include_router(github_oauth_router)
    api.include_router(telegram_connection_router)

    @api.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Return a dependency-free process health signal."""
        return {"status": "ok"}

    if settings.metrics_enabled:

        @api.get("/metrics", include_in_schema=False)
        async def prometheus_metrics() -> PlainTextResponse:
            return PlainTextResponse(
                metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8"
            )

    return api


app = create_app()
