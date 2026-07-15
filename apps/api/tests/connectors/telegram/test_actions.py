from uuid import uuid4

import httpx
import pytest

from app.connectors.base import ConnectorExecutionError
from app.connectors.telegram.actions import TelegramActionConnector
from app.schemas.connector import ConnectorErrorCategory


@pytest.mark.asyncio
async def test_mock_delivery_is_plain_text_idempotent_and_non_reversible() -> None:
    connector = TelegramActionConnector(mock_mode=True)
    action_id = uuid4()
    result = await connector.execute(
        action_id=action_id,
        idempotency_key="message-key",
        input={"chat_id": "demo-chat", "message": "<b>Hello</b> <i>family</i>"},
    )
    again = await connector.execute(
        action_id=action_id,
        idempotency_key="message-key",
        input={"chat_id": "demo-chat", "message": "different"},
    )
    assert result.output["mock"] is True
    assert result.output["reversible"] is False
    assert again == result
    assert connector.delivered_messages == [{"chat_id": "demo-chat", "text": "Hello family", "message_id": result.output["message_id"]}]
    assert (await connector.rollback(action_id=action_id, rollback_payload=None)).output["rolled_back"] is False


@pytest.mark.asyncio
async def test_invalid_chat_is_a_permanent_failure_and_sensitive_text_is_opt_in() -> None:
    connector = TelegramActionConnector(
        bot_token="token",
        transport=httpx.MockTransport(lambda request: httpx.Response(400, json={"ok": False})),
    )
    with pytest.raises(ConnectorExecutionError) as error:
        await connector.execute(action_id=uuid4(), idempotency_key="bad", input={"chat_id": "bad", "message": "hello"})
    assert error.value.category is ConnectorErrorCategory.PERMANENT

    mock = TelegramActionConnector(mock_mode=True)
    await mock.execute(action_id=uuid4(), idempotency_key="safe", input={"chat_id": "chat", "message": "safe", "sensitive_message": "secret"})
    assert mock.delivered_messages[0]["text"] == "safe"
