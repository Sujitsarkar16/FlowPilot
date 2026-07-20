"""Secure HTTP response and request-size defaults."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, production: bool = False) -> None:
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'self'; base-uri 'self'; frame-ancestors 'none'",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
            }
        )
        if self.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_bytes: int, attachment_max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes
        self.attachment_max_bytes = attachment_max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        is_attachment_upload = (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/events/")
            and request.url.path.endswith("/attachments")
        )
        max_bytes = self.attachment_max_bytes if is_attachment_upload else self.max_bytes
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": {"code": "invalid_content_length"}}
                )
            if declared_size < 0:
                return JSONResponse(
                    status_code=400, content={"detail": {"code": "invalid_content_length"}}
                )
            if declared_size > max_bytes:
                return self._too_large()
        if len(await request.body()) > max_bytes:
            return self._too_large()
        return await call_next(request)

    @staticmethod
    def _too_large() -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={"detail": {"code": "request_body_too_large"}},
        )
