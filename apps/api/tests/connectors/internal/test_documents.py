from uuid import uuid4

import pytest

from app.connectors.internal.documents import InternalDocumentConnector


@pytest.mark.asyncio
async def test_documents_use_event_entities_and_strip_html_deterministically() -> None:
    connector = InternalDocumentConnector()
    event = {
        "summary": "<b>Summer trip</b>",
        "entities": [
            {"kind": "destination", "value": {"name": "<i>Lisbon</i>"}},
            {"kind": "date", "value": {"date": "2030-06-01"}},
            {"kind": "pnr", "value": {"value": "secret"}, "is_sensitive": True},
        ],
    }
    input = {"document_type": "itinerary", "event": event, "content": "<script>bad()</script>Check bags"}
    first = await connector.execute(action_id=uuid4(), idempotency_key="document-key", input=input)
    second = await connector.execute(action_id=uuid4(), idempotency_key="document-key", input=input)
    content = first.output["content"]
    assert "Lisbon" in content and "2030-06-01" in content
    assert "<" not in content and "secret" not in content
    assert "bad() Check bags" in content
    assert first == second
    assert await connector.verify(action_id=uuid4(), idempotency_key="document-key", result=first)


@pytest.mark.asyncio
async def test_optional_entities_and_content_do_not_block_generation() -> None:
    result = await InternalDocumentConnector().execute(
        action_id=uuid4(), idempotency_key="invoice", input={"document_type": "invoice_template"}
    )
    assert result.output["filename"].endswith(".md")
    assert "Client" in result.output["content"]
