"""Connector execution contracts that never expose credentials."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConnectorErrorCategory(StrEnum):
    RETRYABLE = "retryable"
    PERMANENT = "permanent"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"


class ConnectorExecutionResult(BaseModel):
    """Validated, serializable outcome returned by a connector implementation."""

    model_config = ConfigDict(extra="forbid")

    output: dict[str, Any] = Field(default_factory=dict)
    rollback_payload: dict[str, Any] | None = None


class ConnectorRollbackResult(BaseModel):
    """Validated result of a safe compensating connector operation."""

    model_config = ConfigDict(extra="forbid")

    output: dict[str, Any] = Field(default_factory=dict)
