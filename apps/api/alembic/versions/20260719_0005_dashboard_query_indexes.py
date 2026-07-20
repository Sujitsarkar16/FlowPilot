"""Add indexes for dashboard summaries and newest-first event pages.

Revision ID: 20260719_0005
Revises: 20260715_0004
"""

import sqlalchemy as sa

from alembic import op

revision = "20260719_0005"
down_revision = "20260715_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_life_events_user_created_id", "life_events", ["user_id", "created_at", "id"]
    )
    op.create_index(
        "ix_plans_user_source_created_id",
        "plans",
        ["user_id", "source_event_id", "created_at", "id"],
    )
    op.create_index("ix_actions_plan_status", "actions", ["plan_id", "status"])
    op.create_index(
        "ix_approvals_active_action_expiry",
        "approvals",
        ["action_id", "expires_at"],
        postgresql_where=sa.text("decision IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_approvals_active_action_expiry", table_name="approvals")
    op.drop_index("ix_actions_plan_status", table_name="actions")
    op.drop_index("ix_plans_user_source_created_id", table_name="plans")
    op.drop_index("ix_life_events_user_created_id", table_name="life_events")
