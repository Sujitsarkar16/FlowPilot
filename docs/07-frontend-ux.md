# Frontend UX specification

## Product feeling

Use a light neutral canvas, white cards, deep indigo/lavender accents, restrained shadows, rounded plan nodes, and explicit green/yellow/red risk indicators. The interface must feel like a premium control centre—not a chat transcript, agent terminal, or n8n-style editor.

## Required screens

### Life Feed

Show greeting, events handled, approvals pending, and time saved. A travel card shows the trip and concise outcome checklist, with **Review plan** and **Approve message** actions. Cards must reveal only safe redacted facts by default.

### Standing Orders

List active rules with natural-language instructions, autonomy scope, and enable state. A single “From now on, whenever…” entry creates a draft rule; show its compiled event/actions/approval policy before saving.

### Event Detail

Show original event (redacted), extracted facts with confidence, AI interpretation, Plan Manifest, DAG, approvals, action outputs, execution timeline, and undo controls. Every action has a **Why?** explanation using stored policy/context provenance.

### Autonomy Centre

Present per-domain controls: calendar, file organisation, drafting, message sending, sharing, repositories, and finance. Clearly label finance as never automatic. Show daily autonomy budgets and trusted-contact rules.

### Personal Graph

Visualize a limited, permission-aware graph linking the user to family, clients, trips, goals, and projects. Avoid making it the primary navigation surface.

## UI states

Support loading, empty, connector disconnected, shadow-mode, pending approval, executing, verified, failed with retry, blocked by policy, and undo-in-progress. The action button must explain why it is unavailable.

## Plan Manifest

Always display objective, action counts by decision, external services, sensitive data categories, estimated completion, and explicit blocked/approval-required actions before a user authorizes a consequential step.

## Accessibility

Use keyboard-operable approval/undo controls, semantic timeline markup, labels beyond color for risk/status, focus management in approval dialogs, responsive card layouts, and readable timestamps in the user's timezone.
