import { describe, expect, it } from "vitest";

import { createApiClient } from "@/lib/api/client";
import { createMockServer, json } from "@/tests/mocks/server";
import { MockEventSource } from "@/tests/mocks/sse";

describe("test API utilities", () => {
  it("serves API-client requests without a backend", async () => {
    const server = createMockServer({
      "GET /api/v1/dashboard/summary": () => json({ events_today: 1 }),
    });
    const api = createApiClient({
      baseUrl: "http://flowpilot.test",
      fetchFn: server.fetch,
      getAccessToken: async () => null,
    });
    await expect(api.getDashboardSummary()).resolves.toMatchObject({ events_today: 1 });
    expect(server.fetch).toHaveBeenCalledOnce();
  });

  it("delivers deterministic SSE payloads", () => {
    const source = new MockEventSource("/events");
    const seen: unknown[] = [];
    source.addEventListener("plan.updated", (event) => seen.push(JSON.parse(event.data)));
    source.emit("plan.updated", { id: "plan-1", status: "completed" });
    expect(seen).toEqual([{ id: "plan-1", status: "completed" }]);
  });
});
