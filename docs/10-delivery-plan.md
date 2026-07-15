# Delivery plan

## Build sequence

### Phase 1 — Foundation

Create the monorepo, environment templates, PostgreSQL schema/migrations, Supabase authentication, storage abstraction, canonical event models, lifecycle enums, ledger, and seeded demo user. Establish connector fakes before live integrations.

### Phase 2 — Travel vertical slice

Build Gmail fixture ingestion, `Travel.Booked` classification/extraction, scoped context retrieval, Travel Autopilot standing order, deterministic policy evaluation, persisted DAG, queue/executor, fake Calendar/Drive/Weather/Telegram adapters, verification, and SSE timeline.

### Phase 3 — Control-centre UI

Build Life Feed, Event Detail, Plan Manifest, approval/denial, shadow mode, undo presentation, Standing Orders, and Autonomy Centre. Connect all UI states to persisted API state—not optimistic fabricated success.

### Phase 4 — Secondary demonstrations

Add `Business.ClientOpportunity` with fake GitHub/project-board actions and `Finance.SalaryCredited` with a mock webhook, budget calculations, and recommendation-only results. Add event replay and trusted-contact/autonomy budget checks.

### Phase 5 — Demo hardening

Run the harness scenarios, rehearse connector failures, redaction, blocked actions, approval expiry, and replay. Seed a stable demo account and fixtures; document every environment variable and use no real financial permissions.

## Demo script (four minutes)

1. Open the Life Feed and show a newly detected Bengaluru flight.
2. Open Event Detail: show extracted facts, minimal context, Plan Manifest, and green/yellow decisions.
3. Stream automatic Calendar/Drive/Weather/checklist outcomes into the timeline.
4. Explain why the family update is awaiting approval, approve it, and show verified delivery.
5. Switch to Shadow Mode/replay to demonstrate user control and explainability.
6. Show a client opportunity and mock salary event to prove the architecture generalizes—then highlight that transfers remain blocked.

## Definition of done

The team can reset data, seed fixtures, run the complete travel demo offline/sandboxed, observe each action in the ledger/UI, approve exactly one message, and show that a red financial action cannot execute. Defer live OAuth polish and extra integrations until this path is reliable.
