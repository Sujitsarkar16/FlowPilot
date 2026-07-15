import type { CompiledStandingOrderRule, StandingOrderActionTemplate } from "@/lib/standing-order-types";

export type AutonomyLevel = "observe" | "suggest" | "safe_actions";
export type ConnectionProvider = "google" | "github" | "telegram" | "mock_bank";
export type ConnectionStatus = "connected" | "error" | "revoked";

/** Safe connection metadata returned by the API; credential material is intentionally excluded. */
export interface Connection {
  id: string;
  provider: ConnectionProvider;
  provider_account_id: string;
  status: ConnectionStatus;
  scopes: string[];
  created_at: string;
  updated_at: string;
}

export interface OAuthStartResponse {
  authorization_url: string;
}

export interface TelegramConnectionInput {
  bot_token: string;
  chat_id: string;
}

export type RiskLevel = "green" | "yellow" | "red";
export type ApprovalDecision = "approved" | "rejected";

export interface ApprovalAction {
  id: string;
  action_type: string;
  connector: string;
  input: Record<string, unknown>;
  status: "planned" | "blocked" | "waiting_approval" | "approved" | "queued" | "running" | "completed" | "failed" | "cancelled" | "rolled_back";
  risk_level: RiskLevel;
  requires_approval: boolean;
  policy_reason: string | null;
  completed_at: string | null;
}

export interface Approval {
  id: string;
  action_id: string;
  decision: ApprovalDecision | "expired" | null;
  expires_at: string;
  decided_at: string | null;
  decided_by_user_id: string | null;
  action: ApprovalAction;
}

export interface CurrentUser {
  id: string;
  email: string | null;
  display_name: string | null;
  default_autonomy: AutonomyLevel;
}

export type LifeEventType =
  | "travel_booked"
  | "travel_changed"
  | "client_opportunity"
  | "client_confirmed"
  | "salary_credited"
  | "subscription_renewal"
  | "generic_important_event";

export type RawEventStatus = "received" | "normalized" | "duplicate" | "failed";

export interface ManualEventInput {
  text: string;
  category_hint?: string | null;
}

export interface ManualEventResponse {
  id: string;
  raw_event_id: string;
  type: LifeEventType;
  status: RawEventStatus;
  is_duplicate: boolean;
}

export interface StandingOrder {
  id: string;
  instruction: string;
  compiled_rule: CompiledStandingOrderRule | null;
  version: number;
  enabled: boolean;
  compilation_status: "pending" | "compiled" | "failed";
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface StandingOrderCreateInput {
  instruction: string;
}

export interface StandingOrderUpdateInput {
  instruction?: string;
  enabled?: boolean;
}

export interface StandingOrderSimulation {
  event_type: LifeEventType;
  matched: boolean;
  proposed_actions: StandingOrderActionTemplate[];
  warnings: string[];
}

export interface ApiValidationIssue {
  loc?: Array<string | number>;
  msg: string;
  type?: string;
}

export interface ApiErrorBody {
  detail?: string | ApiValidationIssue[];
  message?: string;
  error?: string;
}

export interface ApiRequestOptions {
  method?: "DELETE" | "GET" | "PATCH" | "POST" | "PUT";
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
  timeoutMs?: number;
}

export interface ApiClient {
  request<T>(path: string, options?: ApiRequestOptions): Promise<T>;
  getMe(options?: Omit<ApiRequestOptions, "method">): Promise<CurrentUser>;
  createManualEvent(
    input: ManualEventInput,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<ManualEventResponse>;
  listStandingOrders(options?: Omit<ApiRequestOptions, "method">): Promise<StandingOrder[]>;
  createStandingOrder(
    input: StandingOrderCreateInput,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<StandingOrder>;
  updateStandingOrder(
    orderId: string,
    input: StandingOrderUpdateInput,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<StandingOrder>;
  deleteStandingOrder(orderId: string, options?: Omit<ApiRequestOptions, "method">): Promise<void>;
  simulateStandingOrder(
    orderId: string,
    sampleEvent: string,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<StandingOrderSimulation>;
  listPendingApprovals(options?: Omit<ApiRequestOptions, "method">): Promise<Approval[]>;
  approveApproval(
    approvalId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<Approval>;
  rejectApproval(
    approvalId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<Approval>;
  listConnections(options?: Omit<ApiRequestOptions, "method">): Promise<Connection[]>;
  startOAuth(
    provider: "google" | "github",
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<OAuthStartResponse>;
  setupTelegram(
    input: TelegramConnectionInput,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<Connection>;
  testConnection(
    connectionId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<Connection>;
  disconnect(
    connectionId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<void>;
}
