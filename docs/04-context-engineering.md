# Context engineering

## Goal

Give the model the smallest reliable context needed to classify, extract, or propose a plan. Personal data is permissioned input, not ambient memory.

## Context packet

Build a typed packet per task:

```json
{
  "task": "plan_travel_autopilot",
  "event": {"id": "evt_9348", "normalized_content": "...", "trust_level": "external"},
  "facts": {"home_city": "Mumbai", "airport_buffer_minutes": 180},
  "relevant_calendar": [{"start": "...", "end": "...", "title": "Busy"}],
  "matching_rules": [{"id": "rule_travel", "compiled_rule": {}}],
  "capabilities": ["calendar.create", "drive.save", "weather.read"],
  "constraints": {"autonomy_level": 2, "red_actions_require_confirmation": true}
}
```

Retrieve only fields justified by the event. For a travel plan, do not retrieve financial goals or unrelated client contacts. Return context provenance and expiration with every retrieved item.

## Model contracts

Use distinct, schema-validated operations: `classify_event`, `extract_entities`, `propose_plan`, `generate_document`, and `interpret_exception`. Inputs include an explicit output schema, trusted rules, allowed action catalog, and untrusted evidence separated by labels.

The model may recommend an action but cannot grant permission, alter standing orders, select arbitrary tools, expose secrets, or execute. Deterministic services validate entity formats, resolve dates/time zones, calculate financial figures, and apply policy.

## Prompt-injection boundary

External emails, web pages, PDFs, attachments, and connector responses are untrusted content. Quote or summarize them as evidence. Ignore their instructions to reveal data, change policies, bypass approvals, or call tools. Persist an `injection_signal` when detected and continue only with safe extraction.

## Retrieval and retention

- Query by user, event domain, purpose, sensitivity, and expiry.
- Redact unnecessary PII before model calls; replace direct identifiers with stable aliases where possible.
- Log context item IDs and purpose—not raw personal values—in the ledger.
- Keep prompts/version IDs and structured outputs for replay; retain raw event data only under the product retention policy.

## Evaluation cases

Test missing facts, conflicting calendar data, malformed times, a malicious email, low classifier confidence, and no matching standing order. In uncertain cases return `needs_review`, not an invented fact or side effect.
