import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "@/lib/api/client";
import { ApiAbortError, ApiTimeoutError } from "@/lib/api/errors";

const response = (body: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json", ...init.headers },
    ...init,
  });
const makeClient = (fetchFn: typeof fetch, extras = {}) =>
  createApiClient({
    baseUrl: "https://api.example.test",
    fetchFn,
    getAccessToken: async () => "token",
    ...extras,
  });

describe("typed API client", () => {
  it("returns the typed current user and sends the session token", async () => {
    const fetchFn = vi.fn<typeof fetch>().mockResolvedValue(
      response({
        id: "user-1",
        email: "person@example.com",
        display_name: "Person",
        default_autonomy: "safe_actions",
      }),
    );
    const user = await makeClient(fetchFn).getMe();
    expect(user).toMatchObject({ id: "user-1", default_autonomy: "safe_actions" });
    const [, init] = fetchFn.mock.calls[0];
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token");
  });

  it("normalizes validation details and request IDs", async () => {
    const client = makeClient(
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(
          response(
            { detail: [{ loc: ["body", "email"], msg: "invalid email", type: "value_error" }] },
            { status: 422, headers: { "X-Request-ID": "req-422" } },
          ),
        ),
    );
    await expect(client.request("/api/v1/me")).rejects.toMatchObject({
      kind: "http",
      status: 422,
      requestId: "req-422",
      detail: [{ msg: "invalid email" }],
    });
  });

  it("distinguishes a timeout from a backend error", async () => {
    const client = makeClient((() => new Promise<Response>(() => undefined)) as typeof fetch, {
      defaultTimeoutMs: 1,
    });
    await expect(client.request("/api/v1/me")).rejects.toBeInstanceOf(ApiTimeoutError);
  });

  it("distinguishes a caller abort", async () => {
    const controller = new AbortController();
    const fetchFn = vi.fn<typeof fetch>().mockImplementation((_, init) => {
      if (init?.signal?.aborted) return Promise.reject(new DOMException("Aborted", "AbortError"));
      return new Promise((_, reject) =>
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("Aborted", "AbortError")),
        ),
      );
    });
    const client = makeClient(fetchFn, {
      getAccessToken: async () => {
        controller.abort();
        return "token";
      },
    });
    await expect(
      client.request("/api/v1/me", { signal: controller.signal }),
    ).rejects.toBeInstanceOf(ApiAbortError);
  });

  it("invokes configured session handling after a 401", async () => {
    const onUnauthorized = vi.fn();
    const client = makeClient(
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(response({ detail: "Unauthorized" }, { status: 401 })),
      { onUnauthorized },
    );
    await expect(client.getMe()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("uses typed connection endpoints and request bodies", async () => {
    const fetchFn = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response([]))
      .mockResolvedValueOnce(
        response({ authorization_url: "https://accounts.example.test/authorize" }),
      )
      .mockResolvedValueOnce(
        response({
          id: "telegram-1",
          provider: "telegram",
          provider_account_id: "12345",
          status: "connected",
          scopes: [],
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      )
      .mockResolvedValueOnce(
        response({
          id: "telegram-1",
          provider: "telegram",
          provider_account_id: "12345",
          status: "connected",
          scopes: [],
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const client = makeClient(fetchFn);

    await client.listConnections();
    await client.startOAuth("google");
    await client.setupTelegram({ bot_token: "test-token", chat_id: "12345" });
    await client.testConnection("telegram-1");
    await client.disconnect("telegram-1");

    expect(fetchFn.mock.calls.map(([url, init]) => [url, init?.method, init?.body])).toEqual([
      ["https://api.example.test/api/v1/connections", "GET", undefined],
      ["https://api.example.test/api/v1/connections/google/start", "POST", undefined],
      [
        "https://api.example.test/api/v1/connections/telegram",
        "POST",
        JSON.stringify({ bot_token: "test-token", chat_id: "12345" }),
      ],
      ["https://api.example.test/api/v1/connections/telegram-1/test", "POST", undefined],
      ["https://api.example.test/api/v1/connections/telegram-1", "DELETE", undefined],
    ]);
  });
});
