"""Persist user-owned files attached to life events.

Revision ID: 20260719_0006
Revises: 20260719_0005
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260719_0006"
down_revision = "20260719_0005"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "event_attachments",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("life_event_id", UUID, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["life_event_id"], ["life_events.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("life_event_id", "sha256"),
    )
    op.create_index("ix_event_attachments_user_id", "event_attachments", ["user_id"])
    op.create_index("ix_event_attachments_life_event_id", "event_attachments", ["life_event_id"])
    op.create_index(
        "ix_event_attachments_event_created", "event_attachments", ["life_event_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("event_attachments")
