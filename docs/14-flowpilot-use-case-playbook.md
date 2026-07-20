# FlowPilot use-case playbook

Use this guide with live, user-owned data. The dashboard starts empty by design: connect a service or submit a real update; do not add placeholder events to make it look populated.

## 1. Before you start

1. Sign in and open **Connections**. Connect only Google, GitHub, and Telegram accounts you own and intend to use.
2. Open **Preferences**. Set the autonomy level and daily caps deliberately. Keep messaging and all red-risk work approval-gated.
3. Create a **Standing order** describing the outcome you want, its scope, and approval expectations. Start narrow, test it with one event, then expand it.
4. Confirm the dashboard shows only your actual events, plans, approvals, and completed actions.

## The standard FlowPilot loop

1. **Capture:** receive a supported connector event or choose **Tell FlowPilot what happened** for a manual event.
2. **Interpret:** FlowPilot normalizes the input, identifies the life event, and records any sensitive entities with redaction in list views.
3. **Plan:** a matching standing order creates a deterministic action graph. Read the objective, explanation, and each action's risk before executing it.
4. **Policy:** green work may proceed within your autonomy settings; yellow and red work waits when policy requires a decision. Finance never executes automatically.
5. **Review:** use the event detail and approval queue to approve, reject, or inspect each step.
6. **Verify:** check the activity timeline and external artifact (calendar item, Drive document, GitHub repository, or Telegram draft/delivery) before relying on it.

## Example: Travel Autopilot

**Goal:** turn a confirmed trip into an organized, reviewable preparation plan.

1. Connect Google for Gmail, Calendar, and Drive; optionally connect Telegram.
2. Create a standing order such as: “When I confirm travel, organize the trip documents, create calendar reminders, and draft an itinerary. Ask before messaging anyone.”
3. Forward or receive a real booking email, or submit a manual event containing the itinerary details.
4. Open the detected travel event. Verify dates, destination, and confidence before acting.
5. Let permitted work create the travel folder, calendar entries, weather lookup, itinerary, packing checklist, and ticket reference.
6. Review any family or external-message action in **Approvals**. Approve only after reading the recipients and content.
7. Verify the created artifacts and activity timeline. Edit the standing order if the result was too broad or too narrow.

## Example: Client Launch Autopilot

**Goal:** make a repeatable client-project setup without sending commitments automatically.

1. Connect GitHub and Google Drive. Create a standing order that names the workspace, required project documents, and approval requirement for client communication.
2. Submit a real manual event such as “New client project approved; create the private workspace and prepare kickoff materials.”
3. Review the plan before execution: it can prepare a requirements README, private repository, document folder, proposal/invoice templates, and kickoff suggestion.
4. Verify repository visibility, collaborators, and artifacts. Client email or Telegram content stays in approval until you explicitly decide.
5. Use the event timeline as the handoff record; retry only failed actions after correcting the connector or input.

## Example: Salary and budget planning (simulated only)

**Goal:** generate a private budget artifact from a salary event while keeping money movement impossible.

1. Create a standing order with your budget categories and limits. Use a manual salary event or the mock-bank demo boundary only in a non-production environment.
2. Review the generated allocation summary, CSV or spreadsheet artifact, and overspend warning.
3. Treat transfer or purchase suggestions as red proposals. There is no banking transfer connector and FlowPilot must not move money, make purchases, or invest funds.
4. Export or review the budget artifact yourself, then make financial decisions outside FlowPilot.

## Supported use-case boundaries

| Use case | Inputs | Safe output | Always requires review or is unavailable |
| --- | --- | --- | --- |
| Travel preparation | Gmail or manual travel event | Calendar, Drive, weather, itinerary, checklist | Messages to other people require approval |
| Client launch | Manual project event | Private GitHub workspace and planning documents | Client communication and any commitment require approval |
| Subscription renewal | Gmail or manual renewal event | Renewal awareness, a plan, and permitted reminders or checks | Cancellation and any account change require explicit review |
| Appointment or schedule change | Gmail or manual appointment event | Classified event and calendar-oriented planning within preferences | External messages and consequential changes follow policy |
| Personal organization | Generic important event plus standing order | Classified event, plan, reminders, internal documents | Any consequential external action follows policy |
| Salary planning | Manual or mock-bank event in a demo environment | Allocation summary and budget artifact | Transfers, purchases, and investment execution are unavailable |

## Keeping the workspace clear

- Remove an individual event from its detail page only after its plan has no active work; FlowPilot permanently removes its linked event aggregate.
- Disconnect a connector you no longer use from **Connections**. This stops future ingestion; it does not silently erase the audit history.
- An empty dashboard is a valid state. Do not seed demo records in a real workspace.
- A bulk workspace reset deletes persisted user data and is intentionally not automated by page load or this guide. Export anything needed and obtain an explicit, user-scoped confirmation before performing one.

## Troubleshooting and performance

- If an event is absent, confirm the connector is connected, then submit one manual event to verify the workflow independently.
- If a plan waits, read its policy reason and the **Approvals** queue rather than retrying blindly.
- If an action fails, open its detail and correct the connector credentials or input before retrying.
- The dashboard fetches its summary and newest event page in parallel. Keep the database migration current so its user-scoped dashboard indexes are present: `alembic upgrade head` from `apps/api`.

## Safe operating checklist

- Use the minimum connector permissions needed.
- Keep standing orders specific and autonomy conservative until verified.
- Inspect every yellow/red action, recipient, and external artifact.
- Use the audit timeline to understand what happened and when.
- Never use FlowPilot to execute financial transactions.
