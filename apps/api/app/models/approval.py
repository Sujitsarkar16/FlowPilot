"""Human approval records for consequential actions."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApprovalDecision, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.action import Action


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approvals"
    __table_args__ = (
        Index(
            "uq_approvals_active_action",
            "action_id",
            unique=True,
            postgresql_where="decision IS NULL",
        ),
        Index("ix_approvals_pending_expiry", "expires_at", postgresql_where="decision IS NULL"),
    )

    action_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actions.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[ApprovalDecision | None] = mapped_column(db_enum(ApprovalDecision))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    action: Mapped["Action"] = relationship(back_populates="approvals")
