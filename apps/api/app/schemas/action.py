"""Action read schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActionStatus, RiskLevel


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action_type: str
    connector: str
    input: dict[str, Any]
    status: ActionStatus
    risk_level: RiskLevel
    requires_approval: bool
    policy_reason: str | None
    completed_at: datetime | None
    last_error: str | None = None
    depends_on: list[UUID] = []
    rollback_supported: bool = False
