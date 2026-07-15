"""String enums persisted as lowercase values."""

from enum import StrEnum

from sqlalchemy import Enum as SqlEnum


class EventSource(StrEnum):
    MANUAL = "manual"
    GMAIL = "gmail"
    WEBHOOK = "webhook"
    BANKING_MOCK = "banking_mock"
    SYSTEM = "system"


class RawEventStatus(StrEnum):
    RECEIVED = "received"
    NORMALIZED = "normalized"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class LifeEventType(StrEnum):
    TRAVEL_BOOKED = "travel_booked"
    TRAVEL_CHANGED = "travel_changed"
    CLIENT_OPPORTUNITY = "client_opportunity"
    CLIENT_CONFIRMED = "client_confirmed"
    SALARY_CREDITED = "salary_credited"
    SUBSCRIPTION_RENEWAL = "subscription_renewal"
    GENERIC_IMPORTANT_EVENT = "generic_important_event"


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


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ConnectionProvider(StrEnum):
    GOOGLE = "google"
    GITHUB = "github"
    TELEGRAM = "telegram"
    MOCK_BANK = "mock_bank"


class ConnectionStatus(StrEnum):
    CONNECTED = "connected"
    ERROR = "error"
    REVOKED = "revoked"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class AutonomyLevel(StrEnum):
    OBSERVE = "observe"
    SUGGEST = "suggest"
    SAFE_ACTIONS = "safe_actions"


class CompilationStatus(StrEnum):
    PENDING = "pending"
    COMPILED = "compiled"
    FAILED = "failed"


class Importance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def db_enum(enum_type: type[StrEnum]) -> SqlEnum:
    """Persist enum values, never member names."""
    return SqlEnum(enum_type, values_callable=lambda values: [item.value for item in values])
