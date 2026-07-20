# Local development

FlowPilot runs a Next.js web app backed exclusively by Supabase Postgres. All commands below use PowerShell on Windows.

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- Docker Desktop with Docker Compose (optional, only for Mailpit)
- GNU Make from Git for Windows or WSL (optional, only for Mailpit convenience targets)

## Set up local environment files

```powershell
Copy-Item apps\api\.env.example apps\api\.env
Copy-Item apps\web\.env.example apps\web\.env.local
```

The checked-in examples contain no secrets. Add the Supabase connection strings, connector credentials, and authentication credentials only to your untracked local `.env` file.

## Configure Supabase Postgres

```powershell
Set-Location apps\api
# Set DATABASE_URL to the Supabase Session Pooler connection string.
# Set MIGRATIONS_DATABASE_URL to the direct Supabase database connection string.
```

`DATABASE_URL` must be a `postgresql+asyncpg` URL for your Supabase project. Use the Session Pooler for application traffic. `MIGRATIONS_DATABASE_URL` is optional but should use the direct Supabase connection for Alembic migrations, not the transaction pooler.

To inspect development email, start optional Mailpit with `docker compose --profile mail up -d mailpit`, then open `http://localhost:8025`.

Equivalent Make targets are `make dev-api`, `make dev-web`, `make dev-mail`, `make logs-mail`, and `make stop-mail`. Run `make dev-api` and `make dev-web` in separate terminals because both commands stay active.

## Run the API

```powershell
Set-Location apps\api
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Check `http://localhost:8000/health`; it returns `{ "status": "ok" }`.

## Run the web app

In a second terminal:

```powershell
Set-Location apps\web
npm ci
npm run dev
```

Open the localhost URL printed by Next.js.

## Validation

```powershell
Set-Location apps\api
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy app
.venv\Scripts\python -m pytest

Set-Location ..\web
npm run lint
npm run test
npm run typecheck
npm run build
```

## Stop Mailpit

`docker compose --profile mail down` stops optional Mailpit. Supabase database maintenance and backups are managed in the Supabase dashboard; this repository does not create or delete a local database volume.

## Container watch mode

For a Docker-only local workflow, run this command from the repository root and leave it open:

```powershell
docker compose watch
```

Compose Watch synchronizes API and web source changes into development containers. FastAPI reloads when `apps/api/app` changes and Next.js hot-reloads when `apps/web` changes. Changes to a Dockerfile, `pyproject.toml`, `package.json`, or `package-lock.json` automatically rebuild the affected image and restart its service. Stop it with `Ctrl+C`; use `docker compose down` to stop the containers.
