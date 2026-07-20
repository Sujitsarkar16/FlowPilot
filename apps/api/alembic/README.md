# Database migrations

Run migrations with `alembic upgrade head`. To roll back the initial schema, run `alembic downgrade base`; reapply it with `alembic upgrade head`.

Set `MIGRATIONS_DATABASE_URL` to the direct Supabase Postgres connection string before running migrations. If it is omitted, Alembic uses `DATABASE_URL`; do not use a transaction-pooler URL for schema migrations.
