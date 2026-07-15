from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.core.security_headers import RequestBodyLimitMiddleware, SecurityHeadersMiddleware


def test_secure_headers_and_body_limit_are_enforced() -> None:
    app = FastAPI()
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=4)
    app.add_middleware(SecurityHeadersMiddleware, production=True)

    @app.post("/echo")
    async def echo(request: Request) -> Response:
        return Response(content=await request.body())

    client = TestClient(app)
    normal = client.post("/echo", content=b"safe")
    assert normal.status_code == 200
    assert normal.content == b"safe"
    assert normal.headers["X-Content-Type-Options"] == "nosniff"
    assert normal.headers["X-Frame-Options"] == "DENY"
    assert normal.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    oversized = client.post("/echo", content=b"large")
    assert oversized.status_code == 413
    assert oversized.json() == {"detail": {"code": "request_body_too_large"}}
    assert oversized.headers["Content-Security-Policy"].startswith("default-src 'self'")
