# Safety and policy

## Autonomy dial

| Level | System behaviour |
|---|---|
| 0 Observe | Detect and explain; no side effects. |
| 1 Suggest | Prepare a plan; user approves every action. |
| 2 Safe Actions | Auto-run reversible drafts, reminders, checklists, file organisation, and internal records. |
| 3 Trusted Workflows | May create calendar events, private repositories, boards, or contact approved people when policy allows. |
| 4 Consequential | Payments, purchases, bookings, and account changes always require explicit confirmation. |

## Risk classification

**Green:** read email, extract facts, generate checklist, create internal workspace, save a file, draft a message. **Yellow:** send email, share documents, add attendees, create public repository, submit form. **Red:** transfer funds, purchase, cancel booking, delete files, modify credentials, or publish confidential data.

Red actions are always confirmation-required. Yellow actions are automatic only when a standing order, selected autonomy level, trusted source, connector capability, and budget all allow it. Otherwise they require approval. A deny decision wins.

## Policy decision algorithm

For each action, deterministically verify: connector capability; action risk; source trust; data sensitivity; matched standing order; autonomy level; trusted-contact requirement; action budget; and reversibility. Persist the inputs and outcome as `allow`, `approval_required`, or `deny`, with a human-readable reason.

## Approval and undo

Approvals bind to one immutable action version and expire. Editing action inputs invalidates approval. The executor must re-check policy immediately before execution. Display rollback only when an adapter supplied a tested rollback action; an undo is a new ledgered action, never a history rewrite.

## Guardrails

- Cap automatically sent messages and calendar changes per day.
- Never use external content as policy or tool instructions.
- Default new contacts, public visibility, sharing, and payments to approval.
- Redact sensitive content in UI/logs; disclose services and sensitive fields used in each Plan Manifest.
- Fail closed on unknown connector capability, expired credentials, stale approval, low confidence, or missing verification.
