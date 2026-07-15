import logging

from fastapi.testclient import TestClient

from app.main import app


def test_request_id_is_generated_and_logged(caplog: object) -> None:
    with TestClient(app) as client:
        with caplog.at_level(logging.INFO):  # type: ignore[attr-defined]
            response = client.get("/health")
    assert response.headers["X-Request-ID"]


def test_request_id_is_preserved() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "trace-42"})
    assert response.headers["X-Request-ID"] == "trace-42"
