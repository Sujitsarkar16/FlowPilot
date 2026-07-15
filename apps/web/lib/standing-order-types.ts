import type { LifeEventType, RiskLevel } from "@/lib/contracts";

export type ApprovalMode = "automatic" | "approval_required" | "blocked";
export type StandingOrderConnector =
  | "google"
  | "github"
  | "telegram"
  | "mock_bank"
  | "weather"
  | "internal";

export interface EntityCondition {
  field: string;
  operator: "equals" | "contains" | "exists";
  value?: string | number | boolean | null;
}

export interface StandingOrderActionTemplate {
  action_type: string;
  connector: StandingOrderConnector;
  input: Record<string, unknown>;
  risk_level: RiskLevel;
  approval_mode: ApprovalMode;
}

export interface CompiledStandingOrderRule {
  schema_version: "1.0";
  trigger_event_types: LifeEventType[];
  entity_conditions: EntityCondition[];
  action_templates: StandingOrderActionTemplate[];
  explanation: string;
  warnings: string[];
}
