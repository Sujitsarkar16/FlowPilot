"""Append-only audit records; services only expose append operations."""

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, jsonb
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_entries"
    __table_args__ = (Index("ix_audit_entries_event_created", "life_event_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    life_event_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("life_events.id", ondelete="SET NULL"), index=True
    )
    plan_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("plans.id", ondelete="SET NULL"))
    action_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("actions.id", ondelete="SET NULL")
    )
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(jsonb, default=dict, nullable=False)
