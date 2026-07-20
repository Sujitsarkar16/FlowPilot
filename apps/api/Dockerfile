FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN useradd --create-home flowpilot
COPY apps/api /app
RUN pip install --no-cache-dir .

FROM base AS development
COPY --chown=flowpilot:flowpilot apps/api /app
USER flowpilot
EXPOSE 8000
# Bring the schema to head before serving so code and DB never drift out of sync in dev.
# `alembic upgrade head` is a no-op when already current. Production migrates as a deliberate
# deploy step, so its CMD stays migration-free.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app"]

FROM base AS production
USER flowpilot
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
