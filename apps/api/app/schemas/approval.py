"""Approval response schemas; action details are supplied separately."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ApprovalDecision
from app.schemas.action import ActionRead


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action_id: UUID
    decision: ApprovalDecision | None
    expires_at: datetime
    decided_at: datetime | None
    decided_by_user_id: UUID | None
    action: ActionRead
