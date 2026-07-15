"""Encrypted external-provider connection records."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, jsonb
from app.models.enums import ConnectionProvider, ConnectionStatus, db_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Connection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", "provider_account_id"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[ConnectionProvider] = mapped_column(
        db_enum(ConnectionProvider), nullable=False
    )
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ConnectionStatus] = mapped_column(
        db_enum(ConnectionStatus), default=ConnectionStatus.CONNECTED, nullable=False
    )
    encrypted_access_token: Mapped[str | None] = mapped_column(String)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(String)
    # Provider cursors (for example ``gmail_history_id``) live here beside non-secret metadata.
    token_metadata: Mapped[dict[str, Any]] = mapped_column(jsonb, default=dict, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(jsonb, default=list, nullable=False)

    user: Mapped["User"] = relationship(back_populates="connections")
