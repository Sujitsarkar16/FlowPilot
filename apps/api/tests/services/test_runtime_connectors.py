import pytest

from app.core.config import Settings
from app.services.runtime_connectors import RuntimeConnector
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_runtime_internal_connector_generates_all_travel_documents(session) -> None:
    _, _, action = await action_state(session)
    action.action_type = "travel.generate_documents"
    action.connector = "internal"
    await session.commit()

    connector = RuntimeConnector("internal", session, Settings())
    result = await connector.execute(
        action_id=action.id, idempotency_key=action.idempotency_key, input=action.input
    )

    assert {item["document_type"] for item in result.output["documents"]} == {
        "itinerary",
        "packing_checklist",
    }
    assert await connector.verify(
        action_id=action.id, idempotency_key=action.idempotency_key, result=result
    )
