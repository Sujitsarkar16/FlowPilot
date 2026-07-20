import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "@/lib/api/client";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const order = {
  id: "rule-1",
  instruction: "Prepare flights",
  compiled_rule: null,
  version: 1,
  enabled: false,
  compilation_status: "pending",
  last_error: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("standing-order API client", () => {
  it("uses the expected CRUD and simulation routes", async () => {
    const fetchFn = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json([order]))
      .mockResolvedValueOnce(json(order, 201))
      .mockResolvedValueOnce(json({ ...order, enabled: true }))
      .mockResolvedValueOnce(json({ ...order, compilation_status: "compiled" }))
      .mockResolvedValueOnce(
        json({ event_type: "travel_booked", matched: true, proposed_actions: [], warnings: [] }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const client = createApiClient({
      baseUrl: "https://api.example.test",
      fetchFn,
    });
    await client.listStandingOrders();
    await client.createStandingOrder({ instruction: order.instruction });
    await client.updateStandingOrder(order.id, { enabled: true });
    await client.compileStandingOrder(order.id);
    await client.simulateStandingOrder(order.id, "Flight booked");
    await client.deleteStandingOrder(order.id);
    expect(fetchFn.mock.calls.map(([url, init]) => [url, init?.method])).toEqual([
      ["https://api.example.test/api/v1/standing-orders", "GET"],
      ["https://api.example.test/api/v1/standing-orders", "POST"],
      ["https://api.example.test/api/v1/standing-orders/rule-1", "PATCH"],
      ["https://api.example.test/api/v1/standing-orders/rule-1/compile", "POST"],
      ["https://api.example.test/api/v1/standing-orders/rule-1/simulate", "POST"],
      ["https://api.example.test/api/v1/standing-orders/rule-1", "DELETE"],
    ]);
  });
});
