"""Add locally controlled application roles.

Revision ID: 20260720_0007
Revises: 20260719_0006
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260720_0007"
down_revision = "20260719_0006"
branch_labels = None
depends_on = None

user_role = postgresql.ENUM("member", "admin", name="userrole")


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", user_role, nullable=False, server_default=sa.text("'member'")),
    )
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")
    user_role.drop(op.get_bind(), checkfirst=True)
