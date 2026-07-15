from uuid import uuid4

import pytest

from app.connectors.base import ConnectorExecutionError, MockConnector
from app.schemas.connector import ConnectorErrorCategory
from app.services.connector_registry import ConnectorRegistry, ConnectorRegistryError


@pytest.mark.asyncio
async def test_mock_connector_supports_success_retryable_and_permanent_outcomes() -> None:
    success = MockConnector("weather")
    result = await success.execute(action_id=uuid4(), idempotency_key="success", input={})
    assert await success.verify(action_id=uuid4(), idempotency_key="success", result=result)

    retryable = MockConnector("weather", (ConnectorErrorCategory.RETRYABLE,))
    with pytest.raises(ConnectorExecutionError) as retry_error:
        await retryable.execute(action_id=uuid4(), idempotency_key="retry", input={})
    assert retry_error.value.category is ConnectorErrorCategory.RETRYABLE

    permanent = MockConnector("weather", (ConnectorErrorCategory.PERMANENT,))
    with pytest.raises(ConnectorExecutionError) as permanent_error:
        await permanent.execute(action_id=uuid4(), idempotency_key="permanent", input={})
    assert permanent_error.value.category is ConnectorErrorCategory.PERMANENT


def test_registry_rejects_unknown_connector_and_invalid_catalog_input() -> None:
    registry = ConnectorRegistry((MockConnector("weather"),))
    with pytest.raises(ConnectorRegistryError, match="unknown connector"):
        registry.get("missing")
    with pytest.raises(ConnectorRegistryError, match="missing required"):
        registry.validate_input("travel.get_weather", "weather", {})
