"""User persistence model."""

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, jsonb
from app.models.enums import AutonomyLevel, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.connection import Connection
    from app.models.event import RawEvent
    from app.models.personal_context import PersonalContext
    from app.models.plan import Plan
    from app.models.standing_order import StandingOrder


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    default_autonomy: Mapped[AutonomyLevel] = mapped_column(
        db_enum(AutonomyLevel), default=AutonomyLevel.SUGGEST, nullable=False
    )
    autonomy_preferences: Mapped[dict[str, str]] = mapped_column(jsonb, default=dict, nullable=False)
    daily_message_cap: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    daily_calendar_cap: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    connections: Mapped[list["Connection"]] = relationship(back_populates="user")
    standing_orders: Mapped[list["StandingOrder"]] = relationship(back_populates="user")
    raw_events: Mapped[list["RawEvent"]] = relationship(back_populates="user")
    plans: Mapped[list["Plan"]] = relationship(back_populates="user")
    personal_context: Mapped[list["PersonalContext"]] = relationship(back_populates="user")
