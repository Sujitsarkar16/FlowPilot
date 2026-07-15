# End-to-end development plan

## Objective and order of delivery

Deliver a demo-safe PulseOS control centre: a complete Travel Autopilot first, then Client Launch and simulated Salary workflows. Build the durable, policy-governed path before adding live connectors or broader automation.

## Current baseline

The repository has the product contracts, Kiro/Ponytail guidance, FastAPI/Next.js manifests, and fixture data. It does **not** yet have persistence, API routes, policy/execution services, UI screens, fake connector implementations, realtime updates, or deployment automation. Treat the in-memory fixture as disposable demo data.

## Delivery guardrails

- Keep AI as a schema-validated proposal service; deterministic code controls permissions, dates, state, finance, connectors, and retries.
- Preserve tenant isolation, idempotency, immutable approvals, audit records, redaction, and red-action confirmation at every phase.
- Use fake/sandbox connectors only; do not request real Gmail, GitHub, Telegram, bank, or payment credentials for the MVP.
- Add a dependency only when the current platform or existing package cannot meet a demonstrated milestone need.
- Ship vertical slices with their smallest harness scenario and an observable failure/review state.

## Workstreams and ownership

| Stream | Deliverable | Depends on |
|---|---|---|
| Domain/persistence | Schema, migrations, repositories, lifecycle ledger | M0 |
| Orchestration | Interpreter, context, planner, policy, executor | Domain contracts |
| Connectors | Fakes, verification, rollback descriptions | Executor contract |
| API/realtime | Versioned REST, JWT boundary, SSE events | Repositories/services |
| Web | Life Feed, event detail, controls, resilient client | API contract |
| Harness/operations | Fixtures, scenarios, traces, CI/deploy configuration | Each completed slice |

## Ordered milestones

1. **M0 — Lock decisions:** confirm Supabase/PostgreSQL and object-storage choice; record retention, demo user, timezone, autonomy defaults, and fake-connector boundary in `docs/`.
2. **M1 — Local foundation:** finish API entry point, web shell, environment validation, CORS, health check, shared error shape, and reproducible seed/reset command; validate both applications compile/build.
3. **M2 — Durable domain:** introduce PostgreSQL migrations for users, connections, events, interpretations, standing orders, plans, actions, approvals, execution attempts, personal context, and append-only ledger entries; enforce user-scoped queries, lifecycle transitions, idempotency keys, and redacted storage references.
4. **M3 — Event to interpretation:** implement fixture Gmail ingestion, deduplication, canonical-event validation, untrusted-content labeling, deterministic Travel.Booked extractor/classifier fallback, confidence/review handling, and ledger entries.
5. **M4 — Context and plan:** implement scoped context retrieval with provenance/expiry, rule matching, a schema-validated plan proposal adapter, deterministic DAG validation, and a persisted Travel Autopilot plan. Use a fixture/model stub first; add a real provider adapter only after contract evaluation passes.
6. **M5 — Policy and approvals:** classify each planned action, evaluate autonomy/risk/trust/capability/budget, persist reasons, block the family-message send action, reject stale approvals, and re-evaluate policy at execution time.
7. **M6 — Execution and verification:** add idempotent queue/outbox processing, fake Drive/Calendar/Weather/Telegram adapters, bounded retry, result verification, rollback descriptors, and timeline/ledger updates. Calendar, ticket saving, weather, and packing list complete; Telegram remains pending approval.
8. **M7 — Travel UI and realtime:** implement accessible Life Feed, Event Detail, Plan Manifest, timeline, `Why?` explanations, approval/deny modal, undo presentation, and SSE reconnect/reconciliation. Render risk/status with words and color.
9. **M8 — Control features:** implement Standing Orders compilation preview, Autonomy Centre, Shadow Mode, event replay, action budgets, and blocked/retry/disconnected states; do not expose raw policy editing through untrusted input.
10. **M9 — Secondary workflows:** add fixture-backed Client Launch actions (private repository/project-board fakes) and mock Salary webhook calculations/recommendations. Assert no salary workflow can enqueue a money-moving connector action.
11. **M10 — Harness and hardening:** create deterministic fixtures/fakes and scenarios for happy travel, injection, missing data, approval expiry, adapter timeout, verification failure, replay, and salary prohibition; add correlation IDs, structured redacted logs, secret scanning, and release checks.
12. **M11 — Deploy and rehearse:** provision Supabase/Neon, object storage, Vercel, and Cloud Run/Railway; configure encrypted environment secrets, migrations, health checks, CORS, and seeded demo data; rehearse the four-minute demo and rollback/reset procedure.

## Phase exit gates

- **Foundation (M0–M2):** a fresh checkout can configure, migrate, seed, start, and build locally; every persisted record is user-scoped and lifecycle-valid.
- **Travel automation (M3–M6):** one seeded flight produces a persisted, policy-evaluated DAG; green fake actions verify; the yellow send action is impossible to execute before approval; every result has a timeline record.
- **Control centre (M7–M8):** the UI reads only API state, recovers SSE gaps, shows why each decision occurred, supports Shadow Mode/replay, and remains usable by keyboard.
- **Breadth and confidence (M9–M11):** the two secondary demos work with fakes, all documented failure scenarios reach a safe state, deployment uses no real financial authority, and the demo is resettable.

## First implementation ticket

Implement **M1 only**: FastAPI application entry point with health/version endpoint and CORS; Next.js root layout and Life Feed shell; local environment instructions; and compile/build validation. Do not add a database, model provider, connector, or policy engine in this ticket.

## Definition of done

A resettable sandboxed environment can ingest a flight event, show its facts and manifest, automatically verify permitted fake actions, require and record one approval before sending a fake family update, replay safely, demonstrate client/salary alternatives, and prove that a red financial action never executes.