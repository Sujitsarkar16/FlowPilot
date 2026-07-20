import type {
  CompiledStandingOrderRule,
  StandingOrderActionTemplate,
} from "@/lib/standing-order-types";

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
  status:
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

export interface EventAttachmentInputMeta {
  name: string;
  mime_type: string;
  size_bytes: number;
}

export interface EventAttachment {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
}

export interface EventAttachmentContent extends EventAttachment {
  content_base64: string;
}

export interface EventAttachmentUploadInput {
  name: string;
  mime_type: string;
  content_base64: string;
}

export interface ManualEventInput {
  text: string;
  category_hint?: string | null;
  attachments?: EventAttachmentInputMeta[];
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

export interface DashboardSummary {
  events_today: number;
  actions_completed: number;
  pending_approvals: number;
  failed_actions: number;
  time_saved_minutes: number;
}

export interface EventEntity {
  kind: string;
  value: Record<string, unknown>;
  is_sensitive: boolean;
}

export interface EventPlanSummary {
  id: string;
  objective: string;
  status: string;
  action_count: number;
  completed_actions?: number;
  pending_actions?: number;
  failed_actions?: number;
  is_shadow?: boolean;
}

export interface EventListItem {
  id: string;
  type: LifeEventType;
  confidence: number;
  importance: "low" | "medium" | "high";
  summary: string;
  occurred_at: string;
  entities: EventEntity[];
  latest_plan: EventPlanSummary | null;
}

export interface EventDetail extends EventListItem {
  source: string;
  latest_plan: EventPlanSummary | null;
}

export interface EventListQuery {
  cursor?: string;
  limit?: number;
  type?: LifeEventType;
  date_from?: string;
  date_to?: string;
}

export interface EventListResponse {
  items: EventListItem[];
  next_cursor: string | null;
}

export interface TimelineEntry {
  id: string;
  life_event_id: string | null;
  plan_id: string | null;
  action_id: string | null;
  event_name: string;
  actor_type: string;
  request_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface TimelineResponse {
  items: TimelineEntry[];
  next_cursor: string | null;
}

export interface TimelineQuery {
  cursor?: string;
  limit?: number;
}

export interface PlanAction {
  id: string;
  action_type: string;
  connector: string;
  input: Record<string, unknown>;
  status: string;
  risk_level: RiskLevel;
  requires_approval: boolean;
  policy_reason: string | null;
  execution_result?: Record<string, unknown> | null;
  completed_at: string | null;
  last_error?: string | null;
  depends_on?: string[];
  rollback_supported?: boolean;
}

export interface Plan {
  id: string;
  source_event_id: string;
  objective: string;
  summary: string | null;
  planner_rationale: string | null;
  status: string;
  version: number;
  actions: PlanAction[];
  is_shadow?: boolean;
}

export interface Preferences {
  autonomy_level: AutonomyLevel;
  category_behaviors: Record<string, AutonomyLevel>;
  daily_message_cap: number;
  daily_calendar_cap: number;
  fixed_restrictions?: string[];
}

export interface PreferencesUpdateInput {
  autonomy_level: AutonomyLevel;
  category_behaviors: Record<string, AutonomyLevel>;
  daily_message_cap: number;
  daily_calendar_cap: number;
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
  getDashboardSummary(options?: Omit<ApiRequestOptions, "method">): Promise<DashboardSummary>;
  listEvents(
    query?: EventListQuery,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<EventListResponse>;
  getEvent(eventId: string, options?: Omit<ApiRequestOptions, "method">): Promise<EventDetail>;
  deleteEvent(eventId: string, options?: Omit<ApiRequestOptions, "method">): Promise<void>;
  getEventTimeline(
    eventId: string,
    query?: TimelineQuery,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<TimelineResponse>;
  listEventAttachments(
    eventId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<EventAttachment[]>;
  uploadEventAttachment(
    eventId: string,
    input: EventAttachmentUploadInput,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<EventAttachment>;
  getEventAttachmentContent(
    eventId: string,
    attachmentId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<EventAttachmentContent>;
  getPlan(planId: string, options?: Omit<ApiRequestOptions, "method">): Promise<Plan>;
  executePlan(planId: string, options?: Omit<ApiRequestOptions, "method">): Promise<Plan>;
  cancelPlan(planId: string, options?: Omit<ApiRequestOptions, "method">): Promise<Plan>;
  promotePlan(planId: string, options?: Omit<ApiRequestOptions, "method">): Promise<Plan>;
  retryAction(actionId: string, options?: Omit<ApiRequestOptions, "method">): Promise<PlanAction>;
  rollbackAction(
    actionId: string,
    options?: Omit<ApiRequestOptions, "method">,
  ): Promise<PlanAction>;
  getPreferences(options?: Omit<ApiRequestOptions, "method">): Promise<Preferences>;
  updatePreferences(
    input: PreferencesUpdateInput,
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<Preferences>;
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
  compileStandingOrder(
    orderId: string,
    options?: Omit<ApiRequestOptions, "method">,
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
  disconnect(connectionId: string, options?: Omit<ApiRequestOptions, "method">): Promise<void>;
}
