"""Persist Phase M autonomy settings and shadow-plan state.

Revision ID: 20260715_0004
Revises: 20260715_0003
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0004"
down_revision = "20260715_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("autonomy_preferences", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "users", sa.Column("daily_message_cap", sa.Integer(), nullable=False, server_default="10")
    )
    op.add_column(
        "users", sa.Column("daily_calendar_cap", sa.Integer(), nullable=False, server_default="10")
    )
    op.add_column("plans", sa.Column("is_shadow", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "plans", sa.Column("execution_requested", sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column("plans", "execution_requested")
    op.drop_column("plans", "is_shadow")
    op.drop_column("users", "daily_calendar_cap")
    op.drop_column("users", "daily_message_cap")
    op.drop_column("users", "autonomy_preferences")
