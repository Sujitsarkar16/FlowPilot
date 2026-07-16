import pytest
from fastapi.testclient import TestClient

from app import main
from app.core.config import Settings
from app.core.metrics import Metrics


def test_metrics_render_only_bounded_operation_labels() -> None:
    registry = Metrics()
    registry.observe("ingestion", "created", 0.25)
    rendered = registry.render()

    assert 'flowpilot_operations_total{operation="ingestion",outcome="created"} 1' in rendered
    assert 'flowpilot_operation_duration_seconds_sum{operation="ingestion",outcome="created"} 0.25' in rendered
    with pytest.raises(ValueError):
        registry.observe("ingestion", "user-123", 0.1)


def test_metrics_endpoint_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "get_settings", lambda: Settings(metrics_enabled=False))
    with TestClient(main.create_app()) as client:
        assert client.get("/metrics").status_code == 404

    monkeypatch.setattr(main, "get_settings", lambda: Settings(metrics_enabled=True))
    with TestClient(main.create_app()) as client:
        response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "flowpilot_operations_total" in response.text
