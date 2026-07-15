"""Raw source events, normalized life events, and extracted entities."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, jsonb
from app.models.enums import EventSource, Importance, LifeEventType, RawEventStatus, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.user import User


class RawEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "raw_events"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "fingerprint"),
        Index("ix_raw_events_user_status_created", "user_id", "status", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[EventSource] = mapped_column(db_enum(EventSource), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[RawEventStatus] = mapped_column(
        db_enum(RawEventStatus), default=RawEventStatus.RECEIVED, nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(jsonb, default=dict, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True)

    user: Mapped["User"] = relationship(back_populates="raw_events")
    life_event: Mapped["LifeEvent | None"] = relationship(back_populates="raw_event", uselist=False)


class LifeEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "life_events"
    __table_args__ = (Index("ix_life_events_user_type_created", "user_id", "type", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    raw_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("raw_events.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    type: Mapped[LifeEventType] = mapped_column(db_enum(LifeEventType), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    importance: Mapped[Importance] = mapped_column(db_enum(Importance), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    raw_event: Mapped[RawEvent] = relationship(back_populates="life_event")
    entities: Mapped[list["EventEntity"]] = relationship(
        back_populates="life_event", cascade="all, delete-orphan"
    )
    plans: Mapped[list["Plan"]] = relationship(back_populates="source_event")


class EventEntity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_entities"

    life_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("life_events.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(jsonb, default=dict, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    life_event: Mapped[LifeEvent] = relationship(back_populates="entities")
