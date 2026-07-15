# Database migrations

Run migrations with `alembic upgrade head`. To roll back the initial schema, run `alembic downgrade base`; reapply it with `alembic upgrade head`. Use a direct PostgreSQL URL for migrations in production rather than a transaction pooler.
