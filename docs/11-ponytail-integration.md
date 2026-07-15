# Ponytail integration

[Ponytail](https://github.com/DietrichGebert/ponytail) is a development-agent skill, not a FlowPilot runtime dependency. It is installed for this Kiro workspace through `.kiro/steering/ponytail.md`; Kiro loads that steering file for every coding task.

## Why it fits FlowPilot

Ponytail’s ladder—reuse first, platform features before dependencies, then the smallest correct change—keeps a demo build focused on one reliable vertical slice. It is especially useful for avoiding premature connectors, queue infrastructure, component libraries, and abstraction layers.

## Non-negotiable exception

Its minimalism never removes FlowPilot safeguards. Model-output validation, event idempotency, tenant isolation, policy evaluation, approval versioning, red-action confirmation, audit logging, secret redaction, and accessible UI states remain mandatory.

## Initial implementation decisions

- Use FastAPI and Next.js only; do not add Celery, Redis, Tailwind, React Flow, or a database until a demonstrated requirement needs them.
- Start with deterministic in-memory fixture data and fake adapters for the travel demo.
- Use browser `fetch`, native Server-Sent Events, and plain CSS before introducing client/state/UI dependencies.
- Mark the in-memory store as a `ponytail:` limitation and replace it with PostgreSQL before multi-user or durable deployment.

## Working mode

For each slice: read the relevant contract; check whether the capability already exists; implement the smallest safe version; validate it; and record a contract change in `docs/` when necessary. For a full audit or richer command set, install Ponytail in a host with native plugin/skill commands; Kiro’s official adapter provides always-on steering only.

Content was rephrased for compliance with licensing restrictions. Source: [Ponytail repository](https://github.com/DietrichGebert/ponytail).
