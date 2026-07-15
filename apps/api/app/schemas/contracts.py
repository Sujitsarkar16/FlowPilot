"""Versioned boundary contracts mirrored by packages/contracts JSON schemas."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EventSource(StrEnum):
    MANUAL = "manual"
    GMAIL = "gmail"
    WEBHOOK = "webhook"
    BANKING_MOCK = "banking_mock"
    SYSTEM = "system"


class TrustLevel(StrEnum):
    EXTERNAL = "external"
    TRUSTED = "trusted"
    SYSTEM = "system"


class LifeEventType(StrEnum):
    TRAVEL_BOOKED = "travel_booked"
    TRAVEL_CHANGED = "travel_changed"
    CLIENT_OPPORTUNITY = "client_opportunity"
    CLIENT_CONFIRMED = "client_confirmed"
    SALARY_CREDITED = "salary_credited"
    SUBSCRIPTION_RENEWAL = "subscription_renewal"
    GENERIC_IMPORTANT_EVENT = "generic_important_event"


class Importance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    POLICY_CHECKED = "policy_checked"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionStatus(StrEnum):
    PLANNED = "planned"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class RiskLevel(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class PolicyDecision(StrEnum):
    AUTOMATIC = "automatic"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActionResultStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Attachment(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    storage_ref: str = Field(min_length=1)


class RawEvent(ContractModel):
    schema_version: Literal["1.0"]
    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    source: EventSource
    event_type: str = Field(min_length=1)
    actor: str | None = None
    occurred_at: datetime
    payload: dict[str, Any]
    attachments: list[Attachment] = []
    trust_level: TrustLevel
    idempotency_key: str = Field(min_length=1)


class LifeEvent(ContractModel):
    schema_version: Literal["1.0"]
    id: str = Field(min_length=1)
    raw_event_id: str = Field(min_length=1)
    type: LifeEventType
    confidence: float = Field(ge=0, le=1)
    importance: Importance
    requires_follow_up: bool
    entities: dict[str, Any] = {}
    evidence_event_ids: list[str] = Field(min_length=1)


class ActionNode(ContractModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    connector: str = Field(min_length=1)
    input: dict[str, Any]
    status: ActionStatus
    risk_level: RiskLevel
    policy_decision: PolicyDecision
    approval_status: ApprovalStatus
    depends_on: list[str]


class ActionPlan(ContractModel):
    schema_version: Literal["1.0"]
    id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    status: PlanStatus
    actions: list[ActionNode]


class ActionResult(ContractModel):
    schema_version: Literal["1.0"]
    action_id: str = Field(min_length=1)
    status: ActionResultStatus
    external_reference: str | None = None
    output: dict[str, Any]
    verified_at: datetime | None = None
    rollback_supported: bool
    rollback_descriptor: dict[str, Any] | None = None
