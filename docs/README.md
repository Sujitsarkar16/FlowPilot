# FlowPilot build documentation

This folder is the implementation source of truth for the FlowPilot demo MVP. It turns the product brief in [`../Architecture.md`](../Architecture.md) into buildable contracts, constraints, and delivery steps.

## Read in this order

1. [Product scope](01-product-scope.md) — what the MVP does and explicitly does not do.
2. [System architecture](02-system-architecture.md) — services, ownership, and technology choices.
3. [Domain contracts](03-domain-contracts.md) — events, plans, actions, and persistent records.
4. [Context engineering](04-context-engineering.md) — minimum context and model I/O rules.
5. [Safety and policy](05-safety-and-policy.md) — autonomy, risk, approval, and trust boundaries.
6. [API and realtime](06-api-and-realtime.md) — backend/frontend integration contract.
7. [Frontend UX](07-frontend-ux.md) — screens, visual language, and states.
8. [Harness engineering](08-harness-engineering.md) — fixtures, evaluations, observability, and release gates.
9. [Vibe coding workflow](09-vibe-coding-workflow.md) — small, safe implementation loops for humans and coding agents.
10. [Delivery plan](10-delivery-plan.md) — build order and demo path.
11. [Ponytail integration](11-ponytail-integration.md) — minimal-development rules and their FlowPilot safety boundary.
12. [End-to-end development plan](12-end-to-end-development-plan.md) — ordered milestones, dependencies, exit gates, and first ticket.
13. [Frontend architecture — M1](13-frontend-architecture.md) — initial App Router structure and evolution triggers.

## Operating principles

- Build a complete Travel Autopilot, a narrower Client Launch Autopilot, and a simulated Salary Autopilot.
- Treat AI output as an untrusted proposal. Deterministic code owns policy, money, state transitions, dates, connector calls, and retries.
- Retrieve the minimum personal context needed for a task; never place a full personal profile in a model prompt.
- Every consequential action is explainable, auditable, and confirmation-gated when required.
- Prefer mocked connectors for the demo; never move money, make purchases, or alter external accounts automatically.

## Source and decisions

`Architecture.md` defines the product direction. When these documents conflict, preserve safety constraints first, then the explicit MVP scope. Record implementation choices that materially change a contract in the relevant document before writing code.
