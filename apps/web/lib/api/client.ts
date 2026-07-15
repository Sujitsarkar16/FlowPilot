"use client";

import { ApiAbortError, ApiError, ApiTimeoutError } from "@/lib/api/errors";
import type {
  Approval,
  ApiClient,
  ApiErrorBody,
  ApiRequestOptions,
  Connection,
  CurrentUser,
  ManualEventInput,
  ManualEventResponse,
  OAuthStartResponse,
  StandingOrder,
  StandingOrderCreateInput,
  StandingOrderSimulation,
  StandingOrderUpdateInput,
  TelegramConnectionInput,
} from "@/lib/api/types";
import { createClient } from "@/lib/supabase/client";

interface ApiClientOptions {
  baseUrl?: string;
  defaultTimeoutMs?: number;
  fetchFn?: typeof fetch;
  getAccessToken?: () => Promise<string | null>;
  onUnauthorized?: () => Promise<void> | void;
}

function errorMessage(status: number, body: ApiErrorBody | undefined) {
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 422) return "Please correct the highlighted values.";
  if (typeof body?.detail === "string") return body.detail;
  return body?.message ?? body?.error ?? `Request failed with status ${status}.`;
}

async function jsonBody(response: Response) {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

async function browserAccessToken() {
  const { data } = await createClient().auth.getSession();
  return data.session?.access_token ?? null;
}

async function browserUnauthorized() {
  await createClient().auth.signOut();
  if (typeof window !== "undefined") window.location.assign("/login");
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const fetchFn = options.fetchFn ?? fetch;
  const getAccessToken = options.getAccessToken ?? browserAccessToken;
  const onUnauthorized = options.onUnauthorized ?? browserUnauthorized;
  const request = async <T>(path: string, requestOptions: ApiRequestOptions = {}) => {
    const baseUrl = options.baseUrl ?? process.env.NEXT_PUBLIC_API_URL;
    if (!baseUrl)
      throw new ApiError({ kind: "network", message: "The API URL is not configured." });
    const controller = new AbortController();
    const timeoutMs = requestOptions.timeoutMs ?? options.defaultTimeoutMs ?? 15_000;
    let timedOut = false;
    let rejectTimeout!: (reason: unknown) => void;
    const timeoutPromise = new Promise<never>((_, reject) => {
      rejectTimeout = reject;
    });
    const abortFromCaller = () => controller.abort();
    requestOptions.signal?.addEventListener("abort", abortFromCaller, { once: true });
    const timeout = globalThis.setTimeout(() => {
      timedOut = true;
      controller.abort();
      rejectTimeout(new ApiTimeoutError());
    }, timeoutMs);
    try {
      const headers = new Headers(requestOptions.headers);
      headers.set("Accept", "application/json");
      const token = await getAccessToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
      const isFormData = typeof FormData !== "undefined" && requestOptions.body instanceof FormData;
      if (requestOptions.body !== undefined && !isFormData)
        headers.set("Content-Type", "application/json");
      const response = await Promise.race([
        fetchFn(`${baseUrl.replace(/\/$/, "")}${path}`, {
          method: requestOptions.method ?? "GET",
          headers,
          signal: controller.signal,
          body:
            requestOptions.body === undefined || isFormData
              ? (requestOptions.body as BodyInit | undefined)
              : JSON.stringify(requestOptions.body),
        }),
        timeoutPromise,
      ]);
      const body = await jsonBody(response);
      if (!response.ok) {
        const apiBody = body as ApiErrorBody | undefined;
        const error = new ApiError({
          kind: "http",
          status: response.status,
          requestId: response.headers.get("X-Request-ID") ?? undefined,
          detail: apiBody?.detail,
          message: errorMessage(response.status, apiBody),
        });
        if (response.status === 401) {
          try {
            await onUnauthorized();
          } catch {
            /* Preserve the normalized authorization error. */
          }
        }
        throw error;
      }
      return body as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timedOut) throw new ApiTimeoutError();
      if (requestOptions.signal?.aborted || controller.signal.aborted) throw new ApiAbortError();
      throw new ApiError({ kind: "network", message: "The network request failed." });
    } finally {
      window.clearTimeout(timeout);
      requestOptions.signal?.removeEventListener("abort", abortFromCaller);
    }
  };

  return {
    request,
    getMe: (requestOptions) => request<CurrentUser>("/api/v1/me", requestOptions),
    createManualEvent: (input, requestOptions) =>
      request<ManualEventResponse>("/api/v1/events/manual", {
        ...requestOptions,
        body: input as ManualEventInput,
        method: "POST",
      }),
    listStandingOrders: (requestOptions) =>
      request<StandingOrder[]>("/api/v1/standing-orders", requestOptions),
    createStandingOrder: (input, requestOptions) =>
      request<StandingOrder>("/api/v1/standing-orders", {
        ...requestOptions,
        body: input as StandingOrderCreateInput,
        method: "POST",
      }),
    updateStandingOrder: (orderId, input, requestOptions) =>
      request<StandingOrder>(`/api/v1/standing-orders/${orderId}`, {
        ...requestOptions,
        body: input as StandingOrderUpdateInput,
        method: "PATCH",
      }),
    deleteStandingOrder: async (orderId, requestOptions) => {
      await request<void>(`/api/v1/standing-orders/${orderId}`, {
        ...requestOptions,
        method: "DELETE",
      });
    },
    simulateStandingOrder: (orderId, sampleEvent, requestOptions) =>
      request<StandingOrderSimulation>(`/api/v1/standing-orders/${orderId}/simulate`, {
        ...requestOptions,
        body: { sample_event: sampleEvent },
        method: "POST",
      }),
    listPendingApprovals: (requestOptions) =>
      request<Approval[]>("/api/v1/approvals", requestOptions),
    approveApproval: (approvalId, requestOptions) =>
      request<Approval>(`/api/v1/approvals/${approvalId}/approve`, {
        ...requestOptions,
        method: "POST",
      }),
    rejectApproval: (approvalId, requestOptions) =>
      request<Approval>(`/api/v1/approvals/${approvalId}/reject`, {
        ...requestOptions,
        method: "POST",
      }),
    listConnections: (requestOptions) =>
      request<Connection[]>("/api/v1/connections", requestOptions),
    startOAuth: (provider: "google" | "github", requestOptions) =>
      request<OAuthStartResponse>(`/api/v1/connections/${provider}/start`, {
        ...requestOptions,
        method: "POST",
      }),
    setupTelegram: (input, requestOptions) =>
      request<Connection>("/api/v1/connections/telegram", {
        ...requestOptions,
        body: input as TelegramConnectionInput,
        method: "POST",
      }),
    testConnection: (connectionId, requestOptions) =>
      request<Connection>(`/api/v1/connections/${connectionId}/test`, {
        ...requestOptions,
        method: "POST",
      }),
    disconnect: async (connectionId, requestOptions) => {
      await request<void>(`/api/v1/connections/${connectionId}`, {
        ...requestOptions,
        method: "DELETE",
      });
    },
  };
}

export const api = createApiClient();
