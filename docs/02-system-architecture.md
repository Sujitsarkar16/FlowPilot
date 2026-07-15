# System architecture

## Recommended implementation shape

Use a monorepo with `apps/web` (Next.js), `apps/api` (FastAPI), and optional `packages/contracts` for generated/schema-shared types. PostgreSQL is the system of record; object storage holds attachments; a durable queue runs action work.

```text
Connectors → Event Gateway → PostgreSQL event log → Interpreter
                                              ↓
Frontend ← SSE/API ← Ledger/verification ← Executor ← Policy ← Planner
                                      ↑                    ↑
                           Context + Standing Orders ──────┘
```

## Service ownership

| Component | Owns | Must not own |
|---|---|---|
| Event gateway | validation, signature verification, deduplication, normalization | policy decisions |
| Life-event interpreter | classification and entity extraction | direct external side effects |
| Context/rule engine | scoped retrieval and standing-order matching | raw prompt composition outside its contract |
| Planner | structured DAG proposal | permission decisions or connector calls |
| Policy engine | risk, autonomy, approval, allow/deny | language-model judgment |
| Executor | idempotent queued actions, retries, rollback metadata | uncontrolled fan-out |
| Connector adapters | provider translation and verification | business policy |
| Ledger | immutable action history and user timeline | secret storage |

## Technology baseline

- **Web:** Next.js, TypeScript, Tailwind, shadcn/ui, React Flow, SSE.
- **API:** FastAPI, Pydantic, SQLAlchemy/Alembic, PostgreSQL.
- **Async:** Celery + Redis or a PostgreSQL-backed durable job queue.
- **Platform:** Supabase Auth/Storage, with Vercel and Cloud Run/Railway deployment.
- **AI:** a provider-neutral adapter for OpenAI, Gemini, Claude, or Ollama.

## Non-negotiable boundaries

- The model returns validated structured data only; Pydantic rejects malformed output.
- The executor accepts only a policy-approved, persisted action ID—not raw model tool calls.
- Store provider credentials encrypted; logs and prompts must redact tokens, PNRs, emails, and attachment contents.
- Use idempotency keys on ingestion and external action calls.
- Use outbox-style status transitions: `planned → awaiting_approval → queued → running → completed|failed|blocked`.
