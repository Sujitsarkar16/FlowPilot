"""Internal deterministic document-generation connector."""

import hashlib
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.connectors.base import Connector, ConnectorExecutionError
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)
from app.services.document_templates import DocumentTemplateError, DocumentTemplateService


class DocumentInput(BaseModel):
    """Serializable request; event may be a supplied ORM entity during execution."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    document_type: str = Field(min_length=1, max_length=64)
    event: object | None = None
    entities: list[object] = Field(default_factory=list, max_length=50)
    content: str | None = Field(default=None, max_length=20_000)


class InternalDocumentConnector(Connector):
    name = "internal"

    def __init__(self, templates: DocumentTemplateService | None = None) -> None:
        self._templates = templates or DocumentTemplateService()
        self._results: dict[str, ConnectorExecutionResult] = {}

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        if result := self._results.get(idempotency_key):
            return result
        request = self._input(input)
        try:
            document_type = self._templates._aliases.get(request.document_type, request.document_type)
            content = self._templates.render(
                document_type,
                event=request.event,
                entities=request.entities,
                content=request.content,
            )
        except DocumentTemplateError as error:
            raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, str(error)) from error
        filename = f"{document_type}-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]}.md"
        result = ConnectorExecutionResult(
            output={
                "document_type": document_type,
                "filename": filename,
                "content_type": "text/markdown",
                "content": content,
            }
        )
        self._results[idempotency_key] = result
        return result


    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        content = result.output.get("content")
        return (
            result.output.get("content_type") == "text/markdown"
            and isinstance(result.output.get("filename"), str)
            and isinstance(content, str)
            and bool(content)
        )

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        return ConnectorRollbackResult(output={"rolled_back": False, "reason": "document_in_memory"})

    @staticmethod
    def _input(input: Mapping[str, Any]) -> DocumentInput:
        try:
            return DocumentInput.model_validate(dict(input))
        except ValidationError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Invalid document input"
            ) from error
