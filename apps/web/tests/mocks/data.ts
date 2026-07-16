import type { Approval, EventDetail, Plan, StandingOrder } from "@/lib/api/types";

const now = "2026-07-15T10:00:00Z";
export const mockPlan: Plan = {
  id: "plan-1", source_event_id: "event-1", objective: "Prepare the Lisbon trip", summary: "Trip plan", planner_rationale: "Deterministic test plan.", status: "waiting_approval", version: 1, is_shadow: false,
  actions: [{ id: "action-1", action_type: "travel.notify_family", connector: "telegram", input: { message: "Trip ready" }, status: "waiting_approval", risk_level: "yellow", requires_approval: true, policy_reason: "approval_required", completed_at: null, depends_on: [] }],
};
export const mockEvent: EventDetail = {
  id: "event-1", type: "travel_booked", confidence: 0.98, importance: "high", summary: "Flight AA123 to Lisbon", occurred_at: now, source: "manual",
  entities: [{ kind: "destination", value: { name: "Lisbon" }, is_sensitive: false }],
  latest_plan: { id: mockPlan.id, objective: mockPlan.objective, status: mockPlan.status, action_count: 1, pending_actions: 1 },
};
export const mockApproval: Approval = {
  id: "approval-1", action_id: "action-1", decision: null, expires_at: "2026-07-16T10:00:00Z", decided_at: null, decided_by_user_id: null, action: { ...mockPlan.actions[0], status: "waiting_approval" },
};
export const mockOrder: StandingOrder = {
  id: "order-1", instruction: "Prepare every booked flight.", version: 1, enabled: true, compilation_status: "compiled", last_error: null, created_at: now, updated_at: now,
  compiled_rule: { schema_version: "1.0", trigger_event_types: ["travel_booked"], entity_conditions: [], action_templates: [{ action_type: "travel.notify_family", connector: "telegram", input: {}, risk_level: "yellow", approval_mode: "approval_required" }], explanation: "Prepare travel.", warnings: [] },
};
