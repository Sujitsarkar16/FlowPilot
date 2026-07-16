"""Persisted action-plan aggregate."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PlanStatus, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, VersionedMixin

if TYPE_CHECKING:
    from app.models.action import Action
    from app.models.event import LifeEvent
    from app.models.user import User


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "plans"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("life_events.id", ondelete="CASCADE"), index=True
    )
    objective: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    planner_rationale: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PlanStatus] = mapped_column(
        db_enum(PlanStatus), default=PlanStatus.DRAFT, nullable=False
    )
    is_shadow: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="plans")
    source_event: Mapped["LifeEvent"] = relationship(back_populates="plans")
    actions: Mapped[list["Action"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
