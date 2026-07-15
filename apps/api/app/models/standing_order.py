"""Natural-language standing orders and their validated compilation state."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, jsonb
from app.models.enums import CompilationStatus, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, VersionedMixin

if TYPE_CHECKING:
    from app.models.user import User


class StandingOrder(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "standing_orders"
    __table_args__ = (
        CheckConstraint("length(instruction) BETWEEN 1 AND 4000", name="instruction_length"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    compiled_rule: Mapped[dict[str, Any] | None] = mapped_column(jsonb)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compilation_status: Mapped[CompilationStatus] = mapped_column(
        db_enum(CompilationStatus), default=CompilationStatus.PENDING, nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="standing_orders")

    @property
    def is_matchable(self) -> bool:
        """Only successfully compiled and enabled rules may match an event."""
        return self.enabled and self.compilation_status is CompilationStatus.COMPILED
