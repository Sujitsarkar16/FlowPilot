"""Initial PulseOS Phase-B persistence schema.

Revision ID: 20260715_0001
Revises: None
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.models.enums import (
    ActionStatus,
    ApprovalDecision,
    AutonomyLevel,
    CompilationStatus,
    ConnectionProvider,
    ConnectionStatus,
    EventSource,
    Importance,
    JobStatus,
    LifeEventType,
    PlanStatus,
    RawEventStatus,
    RiskLevel,
    db_enum,
)

revision = "20260715_0001"
down_revision = None
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("auth_subject", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("display_name", sa.String(120)),
        sa.Column("default_autonomy", db_enum(AutonomyLevel), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("auth_subject"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_auth_subject", "users", ["auth_subject"])

    op.create_table(
        "connections",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("provider", db_enum(ConnectionProvider), nullable=False),
        sa.Column("provider_account_id", sa.String(255), nullable=False),
        sa.Column("status", db_enum(ConnectionStatus), nullable=False),
        sa.Column("encrypted_access_token", sa.String()),
        sa.Column("encrypted_refresh_token", sa.String()),
        sa.Column("token_metadata", JSONB, nullable=False),
        sa.Column("scopes", JSONB, nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "provider", "provider_account_id"),
    )
    op.create_index("ix_connections_user_id", "connections", ["user_id"])
    op.create_table(
        "personal_context",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("sensitivity", sa.String(32), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_personal_context_user_id", "personal_context", ["user_id"])

    op.create_table(
        "standing_orders",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("compiled_rule", JSONB),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("compilation_status", db_enum(CompilationStatus), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(instruction) BETWEEN 1 AND 4000", name="ck_standing_orders_instruction_length"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_standing_orders_user_id", "standing_orders", ["user_id"])
    op.create_table(
        "raw_events",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("source", db_enum(EventSource), nullable=False),
        sa.Column("source_event_id", sa.String(255)),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("status", db_enum(RawEventStatus), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "source", "fingerprint"),
    )
    op.create_index("ix_raw_events_user_id", "raw_events", ["user_id"])
    op.create_index("ix_raw_events_idempotency_key", "raw_events", ["idempotency_key"])
    op.create_index(
        "ix_raw_events_user_status_created", "raw_events", ["user_id", "status", "created_at"]
    )

    op.create_table(
        "life_events",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("raw_event_id", UUID, nullable=False),
        sa.Column("type", db_enum(LifeEventType), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("importance", db_enum(Importance), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_event_id"], ["raw_events.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("raw_event_id"),
    )
    op.create_index("ix_life_events_user_id", "life_events", ["user_id"])
    op.create_index(
        "ix_life_events_user_type_created", "life_events", ["user_id", "type", "created_at"]
    )
    op.create_table(
        "event_entities",
        sa.Column("life_event_id", UUID, nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["life_event_id"], ["life_events.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_event_entities_life_event_id", "event_entities", ["life_event_id"])

    op.create_table(
        "plans",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("source_event_id", UUID, nullable=False),
        sa.Column("objective", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("status", db_enum(PlanStatus), nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["life_events.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_plans_user_id", "plans", ["user_id"])
    op.create_index("ix_plans_source_event_id", "plans", ["source_event_id"])
    op.create_table(
        "actions",
        sa.Column("plan_id", UUID, nullable=False),
        sa.Column("action_type", sa.String(128), nullable=False),
        sa.Column("connector", sa.String(128), nullable=False),
        sa.Column("input", JSONB, nullable=False),
        sa.Column("status", db_enum(ActionStatus), nullable=False),
        sa.Column("risk_level", db_enum(RiskLevel), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("execution_result", JSONB),
        sa.Column("rollback_payload", JSONB),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "risk_level != 'red' OR requires_approval", name="ck_actions_red_requires_approval"
        ),
        sa.CheckConstraint(
            "status != 'completed' OR completed_at IS NOT NULL",
            name="ck_actions_completed_has_time",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_actions_plan_id", "actions", ["plan_id"])

    op.create_table(
        "action_dependencies",
        sa.Column("action_id", UUID, nullable=False),
        sa.Column("depends_on_action_id", UUID, nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("action_id", "depends_on_action_id"),
    )
    op.create_table(
        "approvals",
        sa.Column("action_id", UUID, nullable=False),
        sa.Column("decision", db_enum(ApprovalDecision)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by_user_id", UUID),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_approvals_action_id", "approvals", ["action_id"])
    op.create_index(
        "ix_approvals_pending_expiry",
        "approvals",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("decision IS NULL"),
    )
    op.create_index(
        "uq_approvals_active_action",
        "approvals",
        ["action_id"],
        unique=True,
        postgresql_where=sa.text("decision IS NULL"),
    )

    op.create_table(
        "jobs",
        sa.Column("action_id", UUID),
        sa.Column("job_type", sa.String(128), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", db_enum(JobStatus), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("lock_owner", sa.String(128)),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_jobs_due", "jobs", ["status", "run_at"])
    op.create_index("uq_jobs_idempotency_key", "jobs", ["idempotency_key"], unique=True)
    op.create_table(
        "audit_entries",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("life_event_id", UUID),
        sa.Column("plan_id", UUID),
        sa.Column("action_id", UUID),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("request_id", sa.String(64)),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["life_event_id"], ["life_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_entries_user_id", "audit_entries", ["user_id"])
    op.create_index("ix_audit_entries_life_event_id", "audit_entries", ["life_event_id"])
    op.create_index("ix_audit_entries_request_id", "audit_entries", ["request_id"])
    op.create_index(
        "ix_audit_entries_event_created", "audit_entries", ["life_event_id", "created_at"]
    )


def downgrade() -> None:
    for index in (
        "ix_audit_entries_event_created",
        "ix_audit_entries_request_id",
        "ix_audit_entries_life_event_id",
        "ix_audit_entries_user_id",
    ):
        op.drop_index(index, table_name="audit_entries")
    op.drop_table("audit_entries")
    op.drop_index("uq_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_due", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("uq_approvals_active_action", table_name="approvals")
    op.drop_index("ix_approvals_pending_expiry", table_name="approvals")
    op.drop_index("ix_approvals_action_id", table_name="approvals")
    op.drop_table("approvals")
    op.drop_table("action_dependencies")
    op.drop_index("ix_actions_plan_id", table_name="actions")
    op.drop_table("actions")
    op.drop_index("ix_plans_source_event_id", table_name="plans")
    op.drop_index("ix_plans_user_id", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_event_entities_life_event_id", table_name="event_entities")
    op.drop_table("event_entities")
    op.drop_index("ix_life_events_user_type_created", table_name="life_events")
    op.drop_index("ix_life_events_user_id", table_name="life_events")
    op.drop_table("life_events")

    op.drop_index("ix_raw_events_user_status_created", table_name="raw_events")
    op.drop_index("ix_raw_events_idempotency_key", table_name="raw_events")
    op.drop_index("ix_raw_events_user_id", table_name="raw_events")
    op.drop_table("raw_events")
    op.drop_index("ix_standing_orders_user_id", table_name="standing_orders")
    op.drop_table("standing_orders")
    op.drop_index("ix_personal_context_user_id", table_name="personal_context")
    op.drop_table("personal_context")
    op.drop_index("ix_connections_user_id", table_name="connections")
    op.drop_table("connections")
    op.drop_index("ix_users_auth_subject", table_name="users")
    op.drop_table("users")

    for enum in (
        "risklevel",
        "actionstatus",
        "planstatus",
        "importance",
        "lifeeventtype",
        "raweventstatus",
        "compilationstatus",
        "connectionstatus",
        "connectionprovider",
        "approvaldecision",
        "jobstatus",
        "eventsource",
        "autonomylevel",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
