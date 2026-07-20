"""User-owned files attached to a life event."""

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EventAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    # ponytail: bounded blobs live in Postgres for a simple, private MVP; move bytes to object
    # storage and retain only metadata here when attachment volume needs independent scaling.
    __tablename__ = "event_attachments"
    __table_args__ = (
        Index("ix_event_attachments_event_created", "life_event_id", "created_at"),
        UniqueConstraint("life_event_id", "sha256"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    life_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("life_events.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
