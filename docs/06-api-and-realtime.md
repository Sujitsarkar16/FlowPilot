# API and realtime contract

## API conventions

Use `/api/v1`, JSON, UTC ISO-8601 timestamps, opaque IDs, and a standard problem response: `{ "code", "message", "request_id", "details" }`. Authenticate every user endpoint through Supabase JWT verification. Connector webhooks use independent signature validation and idempotency keys.

## Essential endpoints

| Method and path | Purpose |
|---|---|
| `POST /events/ingest` | Ingest a normalized mock or connector event. |
| `GET /events` / `GET /events/{id}` | Life Feed and event details. |
| `POST /events/{id}/replay` | Re-plan/re-execute under current policy; preserves original event. |
| `GET /plans/{id}` | Manifest, DAG, policy decisions, and timeline. |
| `POST /actions/{id}/approve` | Record approval for the exact action version. |
| `POST /actions/{id}/deny` | Record denial and unblock dependent failure handling. |
| `POST /actions/{id}/undo` | Queue supported rollback. |
| `GET/POST/PATCH /standing-orders` | List, compile, enable, or edit rules. |
| `GET/PATCH /autonomy` | Read/update user and domain autonomy settings. |
| `POST /webhooks/mock-bank` | Demonstration-only salary event endpoint. |

## Server-sent events

Provide `GET /stream` with authenticated, user-scoped events. Emit `event.created`, `plan.created`, `action.updated`, `approval.requested`, `timeline.appended`, and `connector.status_changed`. Each message includes `id`, `occurred_at`, `resource_id`, and a compact redacted payload.

The web client stores the last SSE ID, reconnects with `Last-Event-ID`, then reconciles by polling the affected resource. SSE improves immediacy; PostgreSQL remains authoritative.

## Example approval request

```json
{
  "action_id": "act_42",
  "action_version": 1,
  "decision": "approve",
  "reason": "Send itinerary update to approved family contacts"
}
```

Return `409` for a stale action version, duplicate terminal decision, or changed policy. Never let a browser submit connector credentials or invoke provider operations directly.
