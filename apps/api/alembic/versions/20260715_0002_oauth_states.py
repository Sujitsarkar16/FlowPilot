"""Persist one-time OAuth state to block replay across instances.

Revision ID: 20260715_0002
Revises: 20260715_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0002"
down_revision = "20260715_0001"
branch_labels = None
depends_on = None


UUID = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("nonce_hash"),
    )
    op.create_index("ix_oauth_states_user_id", "oauth_states", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_oauth_states_user_id", table_name="oauth_states")
    op.drop_table("oauth_states")
