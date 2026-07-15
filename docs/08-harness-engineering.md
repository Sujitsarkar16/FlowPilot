# Harness engineering

Harness engineering makes the agentic workflow dependable: reproducible inputs, executable checks, observable state, and safe recovery—not an impressive one-off demo.

## Local harness components

1. **Fixture factory:** produces deterministic Gmail, client-email, weather, calendar, GitHub, and mock-bank payloads.
2. **Connector fakes:** record calls and simulate success, timeout, rate-limit, invalid credentials, and verification mismatch.
3. **Scenario runner:** submits a fixture, waits for terminal/review state, then asserts persisted plan, actions, ledger, and fake calls.
4. **Evaluation suite:** scores classification, extraction, plan validity, policy adherence, and UI-visible explanations.
5. **Replay console:** reruns an event with a chosen model/prompt/policy version without modifying the original record.

## Minimum deterministic scenarios

| Scenario | Required assertion |
|---|---|
| Flight confirmation | Creates valid travel plan; notification remains pending approval. |
| Malicious flight email | Extracts safe facts; no policy/tool instruction follows email text. |
| Missing departure time | Blocks date-dependent actions and asks for review. |
| Approval expires | Send action remains unexecuted. |
| Connector timeout | Retries only idempotent action; timeline records attempt. |
| Verification failure | Action is not marked completed; manual repair path is visible. |
| Salary webhook | Produces recommendations only; no money-moving connector call exists. |

## Release gates

Before demo/deploy: schema validation passes for every model response; every action has a decision and timeline entry; red actions cannot bypass confirmation; replay is idempotent; secret scanning is clean; fixtures run against connector fakes; and a scripted travel happy path completes.

## Observability

Attach a correlation ID from webhook through event, plan, action, job, adapter call, verification, and SSE notification. Record model/provider/prompt/schema versions, latency, decision reason, redacted context IDs, retry count, and rollback outcome. Do not log tokens, raw sensitive documents, or full prompts containing personal data.

## Failure policy

Favor `blocked`, `needs_review`, or retriable `failed` over guessed success. Automated retries require an idempotency key and bounded exponential backoff. Escalate terminal errors to the Life Feed with a clear repair action.
