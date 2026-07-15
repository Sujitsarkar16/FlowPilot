"""Structured output contract for life-event classification."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Importance, LifeEventType


class Classification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: LifeEventType
    confidence: float = Field(ge=0, le=1)
    importance: Importance
    summary: str = Field(min_length=1, max_length=500)
    reason: str = Field(default="", max_length=500)
