"""Plan read schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlanStatus
from app.schemas.action import ActionRead


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_event_id: UUID
    objective: str
    summary: str | None
    planner_rationale: str | None
    status: PlanStatus
    version: int
    is_shadow: bool = False
    execution_requested: bool = False
    customization_fallback: bool = False  # True when AI customization failed and default plan was used
    actions: list[ActionRead] = Field(default_factory=list)
