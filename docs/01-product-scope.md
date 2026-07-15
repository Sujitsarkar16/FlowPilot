# Product scope

## Outcome

PulseOS is a calm personal control centre: it turns trusted service events into visible, policy-governed action plans while keeping the user in control.

## In scope: three demonstrable workflows

### 1. Travel Autopilot — complete hero workflow

**Trigger:** a flight-confirmation email reaches connected Gmail.

**Automatic work:** detect `Travel.Booked`; extract traveller, airline, flight, PNR, route, terminal, departure time, and attachment; create a trip workspace; save the ticket; create calendar/reminders; check destination weather; and generate a packing list.

**Approval-gated work:** draft a family notification, then request approval before sending it. Show every step, connector result, reason, and rollback option in the timeline.

### 2. Client Launch Autopilot — secondary workflow

Classify a client email as `Business.ClientOpportunity`; extract requirements; create an internal workspace, private GitHub repository, requirement summary, project board, proposal, and invoice template; find kickoff slots; and draft a reply. Sending remains manual approval.

### 3. Salary Autopilot — simulated workflow

Accept only a mock webhook or sandbox transaction. Update a budget, calculate suggested allocations, update a demo spreadsheet, check spending, and create rent/savings reminders. Transfers, purchases, and investment execution are always proposed—not performed.

## Explicit non-goals

No real banking transfers, purchases, travel booking, browser/phone automation, WhatsApp control, broad productivity suite, public repository by default, or autonomous credential/account changes.

## MVP acceptance criteria

- A seeded travel email completes the happy path end-to-end in the UI.
- Every generated action has a risk, policy decision, status, tool result, and timeline entry.
- The send notification action cannot execute without a recorded approval.
- Shadow Mode presents the same plan without connector side effects.
- A seeded client email and salary webhook demonstrate the two secondary workflows.
- The demo can run with mocked or sandbox connectors and no real personal data.
