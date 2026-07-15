# Vibe coding workflow

Vibe coding is fast implementation with an explicit contract, a small change surface, and immediate evidence—not unconstrained generation.

## Rules for each implementation slice

1. Choose one vertical slice from the delivery plan.
2. Read the referenced contract first; do not infer safety or schema behaviour from UI text.
3. State the changed files, invariant, and observable completion condition.
4. Implement the smallest production-shaped version; avoid speculative abstractions and out-of-scope integrations.
5. Run the narrowest relevant fixture, lint/type check, or API smoke check.
6. Record a decision when the change alters a documented interface, policy, or persistence model.

## Suggested task prompt template

```text
Implement [single slice] according to [docs file/section].
Invariant: [safety/data rule].
Inputs and outputs: [contract].
Do not modify: [out-of-scope areas].
Done when: [test/smoke evidence].
Report: files changed, behaviour, validation, and known limitations.
```

## Good slices

- Define Pydantic schemas for canonical events and reject unknown trust levels.
- Ingest a seeded Gmail event idempotently and display it in the Life Feed.
- Add the Travel.Booked classifier adapter with fixture-backed output validation.
- Persist a policy decision that blocks `send_family_notification` until approval.
- Stream an action status update to the Event Detail timeline.

## Avoid

Do not build all connectors at once, allow model-selected arbitrary tools, mix real and demo credentials, add financial execution, replace policy checks with prompt text, or redesign multiple screens while changing a backend contract.

## Review checklist

A slice is ready only if it preserves tenant isolation, records an audit event, has deterministic status transitions, redacts sensitive output, honors the risk policy, and leaves an understandable recovery path. If any point is unknown, stop at a review state rather than guessing.
