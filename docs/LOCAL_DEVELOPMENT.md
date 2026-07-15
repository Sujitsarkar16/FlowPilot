# Local development

PulseOS runs a Next.js web app, FastAPI API, and local PostgreSQL service. All commands below use PowerShell on Windows.

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- Docker Desktop with Docker Compose
- GNU Make from Git for Windows or WSL (optional; direct `docker compose` commands are equivalent)

## Set up local environment files

```powershell
Copy-Item apps\api\.env.example apps\api\.env
Copy-Item apps\web\.env.example apps\web\.env.local
```

The checked-in examples contain no secrets. Add connector or authentication credentials only to your untracked local `.env` file.

## Start infrastructure

```powershell
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U pulseos -d pulseos
```

The local PostgreSQL URL is `postgresql+asyncpg://pulseos:pulseos@localhost:5432/pulseos`. To inspect development email later, start optional Mailpit with `docker compose --profile mail up -d mailpit`, then open `http://localhost:8025`.

Equivalent Make targets are `make dev-api`, `make dev-web`, `make dev-db`, `make dev-mail`, `make logs`, and `make stop`. Run `make dev-api` and `make dev-web` in separate terminals because both commands stay active.

## Run the API

```powershell
Set-Location apps\api
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
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

## Stop and reset

`docker compose down` stops containers while preserving the database volume. `make reset-db` or `docker compose down -v` permanently deletes the local PostgreSQL data volume; use it only when a full local reset is intended.
