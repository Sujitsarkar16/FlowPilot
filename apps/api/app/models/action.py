"""Executable actions and explicit action-dependency edges."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, jsonb
from app.models.enums import ActionStatus, RiskLevel, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, VersionedMixin

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.plan import Plan


class Action(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "actions"
    __table_args__ = (
        CheckConstraint("risk_level != 'red' OR requires_approval", name="red_requires_approval"),
        CheckConstraint(
            "status != 'completed' OR completed_at IS NOT NULL", name="completed_has_time"
        ),
    )

    plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("plans.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    connector: Mapped[str] = mapped_column(String(128), nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(jsonb, default=dict, nullable=False)
    status: Mapped[ActionStatus] = mapped_column(
        db_enum(ActionStatus), default=ActionStatus.PLANNED, nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(db_enum(RiskLevel), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(jsonb)
    rollback_payload: Mapped[dict[str, Any] | None] = mapped_column(jsonb)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    policy_reason: Mapped[str | None] = mapped_column(String(64))

    plan: Mapped["Plan"] = relationship(back_populates="actions")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="action")


class ActionDependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "action_dependencies"
    __table_args__ = (UniqueConstraint("action_id", "depends_on_action_id"),)

    action_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actions.id", ondelete="CASCADE"), nullable=False
    )
    depends_on_action_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actions.id", ondelete="CASCADE"), nullable=False
    )
