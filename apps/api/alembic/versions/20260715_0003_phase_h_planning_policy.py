"""Add persisted planning rationale and action policy decisions.

Revision ID: 20260715_0003
Revises: 20260715_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0003"
down_revision = "20260715_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("planner_rationale", sa.Text(), nullable=True))
    op.add_column("actions", sa.Column("policy_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("actions", "policy_reason")
    op.drop_column("plans", "planner_rationale")
