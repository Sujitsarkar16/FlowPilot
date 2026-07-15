import { describe, expect, it } from "vitest";

import type { ActionPlan, ActionResult, LifeEvent, RawEvent } from "@/lib/contracts";

const rawEvent: RawEvent = {
  schema_version: "1.0",
  id: "evt_9348",
  user_id: "usr_demo",
  source: "gmail",
  event_type: "email.received",
  occurred_at: "2026-07-15T09:30:00+05:30",
  payload: { subject: "Flight confirmed" },
  trust_level: "external",
  idempotency_key: "gmail:message:abc",
};

const lifeEvent: LifeEvent = {
  schema_version: "1.0",
  id: "life_9348",
  raw_event_id: rawEvent.id,
  type: "travel_booked",
  confidence: 0.97,
  importance: "high",
  requires_follow_up: true,
  evidence_event_ids: [rawEvent.id],
};

const actionPlan: ActionPlan = {
  schema_version: "1.0",
  id: "plan_1",
  event_id: lifeEvent.id,
  objective: "Prepare Bengaluru trip",
  status: "waiting_approval",
  actions: [],
};

const actionResult: ActionResult = {
  schema_version: "1.0",
  action_id: "act_1",
  status: "verified",
  output: {},
  rollback_supported: false,
};

describe("shared contract types", () => {
  it("preserves the versioned schema fields", () => {
    expect([rawEvent, lifeEvent, actionPlan, actionResult]).toHaveLength(4);
    expect(actionPlan.event_id).toBe(lifeEvent.id);
  });
});
