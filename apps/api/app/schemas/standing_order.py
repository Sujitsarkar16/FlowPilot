"""API and simulation schemas for user-scoped standing orders."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CompilationStatus, LifeEventType
from app.schemas.compiled_rule import ActionTemplate, CompiledRule
from app.schemas.raw_sources import MAX_CONTENT_CHARS

MAX_INSTRUCTION_LENGTH = 4_000
MAX_RULE_BYTES = 32_768


class StandingOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(min_length=1, max_length=MAX_INSTRUCTION_LENGTH)
    # Kept for validated imports and direct service use; normal API creation compiles text.
    compiled_rule: CompiledRule | None = None

    @field_validator("compiled_rule", mode="before")
    @classmethod
    def limit_rule_size(cls, rule: object) -> object:
        if rule is not None:
            serialized = rule.model_dump_json() if isinstance(rule, CompiledRule) else str(rule)
            if len(serialized.encode()) > MAX_RULE_BYTES:
                raise ValueError("compiled rule exceeds the safe size limit")
        return rule


class StandingOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str | None = Field(default=None, min_length=1, max_length=MAX_INSTRUCTION_LENGTH)
    enabled: bool | None = None


class StandingOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instruction: str
    compiled_rule: CompiledRule | None
    version: int
    enabled: bool
    compilation_status: CompilationStatus
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class StandingOrderSimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_event: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)


class StandingOrderSimulation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: LifeEventType
    matched: bool
    proposed_actions: list[ActionTemplate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
