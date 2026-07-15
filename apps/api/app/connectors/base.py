"""Provider-neutral action metadata and safe execution contract."""

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal
from uuid import UUID

from app.models.enums import ConnectionProvider, RiskLevel
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)

ApprovalMode = Literal["automatic", "approval_required", "blocked"]
ConnectorName = Literal["google", "github", "telegram", "mock_bank", "weather", "internal"]


class ConnectorExecutionError(Exception):
    """A connector failure with an explicit retry and disclosure category."""

    def __init__(self, category: ConnectorErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class Connector(ABC):
    """Execution boundary: action input enters, credentials stay inside the connector."""

    name: str

    @abstractmethod
    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        """Perform an idempotent action and return only serializable result data."""

    @abstractmethod
    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        """Confirm that a successful connector call reached the intended external state."""

    @abstractmethod
    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        """Apply a safe compensating operation when the registered action is reversible."""


class MockConnector(Connector):
    """Deterministic in-process connector used until provider implementations are installed."""

    def __init__(
        self, name: str = "mock", outcomes: tuple[ConnectorErrorCategory | None, ...] = ()
    ) -> None:
        self.name = name
        self._outcomes = deque(outcomes)
        self.executions: list[dict[str, Any]] = []
        self.rollbacks: list[dict[str, Any]] = []

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        outcome = self._outcomes.popleft() if self._outcomes else None
        if outcome is not None:
            raise ConnectorExecutionError(outcome, f"Mock {outcome.value} failure")
        record = {"action_id": str(action_id), "idempotency_key": idempotency_key}
        self.executions.append(record)
        return ConnectorExecutionResult(
            output={"mock": True, **record}, rollback_payload={"mock_action_id": str(action_id)}
        )

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        return result.output.get("idempotency_key") == idempotency_key

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        record = {"action_id": str(action_id), "rollback_payload": dict(rollback_payload or {})}
        self.rollbacks.append(record)
        return ConnectorRollbackResult(output={"mock": True, "rolled_back": True})


@dataclass(frozen=True, slots=True)
class InputField:
    """A frontend-safe declaration for one action input."""

    value_type: Literal["string", "number", "boolean", "object", "array"]
    required: bool = False
    description: str = ""

    def metadata(self) -> dict[str, object]:
        return {
            "type": self.value_type,
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    """Static policy and connector requirements for a supported action."""

    action_type: str
    connector: ConnectorName
    default_risk: RiskLevel
    minimum_risk: RiskLevel
    reversible: bool
    required_scopes: tuple[str, ...]
    provider: ConnectionProvider | str | None
    input_schema: Mapping[str, InputField]
    minimum_approval: ApprovalMode

    def __post_init__(self) -> None:
        if not self.action_type or "." not in self.action_type:
            raise ValueError("action_type must be a namespaced non-empty string")
        if isinstance(self.provider, str) and not self.provider:
            raise ValueError("provider must be non-empty when supplied")
        if len(self.required_scopes) != len(set(self.required_scopes)):
            raise ValueError(f"{self.action_type} has duplicate required scopes")
        object.__setattr__(self, "input_schema", MappingProxyType(dict(self.input_schema)))

    def frontend_metadata(self) -> dict[str, object]:
        """Return only serializable, non-secret metadata suitable for clients."""
        return {
            "action_type": self.action_type,
            "connector": self.connector,
            "default_risk": self.default_risk.value,
            "minimum_risk": self.minimum_risk.value,
            "reversible": self.reversible,
            "required_scopes": list(self.required_scopes),
            "provider": self.provider.value
            if isinstance(self.provider, ConnectionProvider)
            else self.provider,
            "input_schema": {
                name: field.metadata() for name, field in sorted(self.input_schema.items())
            },
            "minimum_approval": self.minimum_approval,
        }
