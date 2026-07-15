export type SchemaVersion = "1.0";

export type EventSource = "manual" | "gmail" | "webhook" | "banking_mock" | "system";
export type TrustLevel = "external" | "trusted" | "system";
export type LifeEventType =
  | "travel_booked"
  | "travel_changed"
  | "client_opportunity"
  | "client_confirmed"
  | "salary_credited"
  | "subscription_renewal"
  | "generic_important_event";
export type Importance = "low" | "medium" | "high";
export type PlanStatus =
  | "draft"
  | "policy_checked"
  | "running"
  | "waiting_approval"
  | "completed"
  | "partially_completed"
  | "failed"
  | "cancelled";
export type ActionStatus =
  | "planned"
  | "blocked"
  | "waiting_approval"
  | "approved"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "rolled_back";
export type RiskLevel = "green" | "yellow" | "red";
export type PolicyDecision = "automatic" | "approval_required" | "blocked";
export type ApprovalStatus = "not_required" | "pending" | "approved" | "rejected";
export type ActionResultStatus = "verified" | "failed" | "rolled_back";

export interface Attachment {
  id: string;
  name: string;
  storage_ref: string;
}

export interface RawEvent {
  schema_version: SchemaVersion;
  id: string;
  user_id: string;
  source: EventSource;
  event_type: string;
  actor?: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  attachments?: Attachment[];
  trust_level: TrustLevel;
  idempotency_key: string;
}

export interface LifeEvent {
  schema_version: SchemaVersion;
  id: string;
  raw_event_id: string;
  type: LifeEventType;
  confidence: number;
  importance: Importance;
  requires_follow_up: boolean;
  entities?: Record<string, unknown>;
  evidence_event_ids: string[];
}

export interface ActionNode {
  id: string;
  type: string;
  connector: string;
  input: Record<string, unknown>;
  status: ActionStatus;
  risk_level: RiskLevel;
  policy_decision: PolicyDecision;
  approval_status: ApprovalStatus;
  depends_on: string[];
}

export interface ActionPlan {
  schema_version: SchemaVersion;
  id: string;
  event_id: string;
  objective: string;
  status: PlanStatus;
  actions: ActionNode[];
}

export interface ActionResult {
  schema_version: SchemaVersion;
  action_id: string;
  status: ActionResultStatus;
  external_reference?: string;
  output: Record<string, unknown>;
  verified_at?: string;
  rollback_supported: boolean;
  rollback_descriptor?: Record<string, unknown>;
}
