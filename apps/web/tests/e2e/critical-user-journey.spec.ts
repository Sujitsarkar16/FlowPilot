import { expect, test, type Page } from "@playwright/test";

const now = "2026-07-15T10:00:00Z";
function plan(completed = false) {
  return {
    id: "plan-1",
    source_event_id: "event-1",
    objective: "Prepare the Lisbon trip",
    summary: "Trip plan",
    planner_rationale: "Test plan",
    status: completed ? "completed" : "waiting_approval",
    version: 1,
    actions: [
      {
        id: "action-1",
        action_type: "travel.notify_family",
        connector: "telegram",
        input: { message: "Trip ready" },
        status: completed ? "completed" : "waiting_approval",
        risk_level: "yellow",
        requires_approval: true,
        policy_reason: "approval_required",
        completed_at: completed ? now : null,
        depends_on: [],
      },
    ],
  };
}
async function useDemoApi(page: Page) {
  let approved = false;
  await page.route("**/*", async (route) => {
    const request = route.request(),
      url = new URL(request.url()),
      path = url.pathname;
    if (!path.startsWith("/api/v1/")) return route.fallback();
    const event = {
      id: "event-1",
      type: "travel_booked",
      confidence: 0.98,
      importance: "high",
      summary: "Flight AA123 to Lisbon",
      occurred_at: now,
      entities: [{ kind: "destination", value: { name: "Lisbon" }, is_sensitive: false }],
    };
    const body = path.endsWith("/dashboard/summary")
      ? {
          events_today: 1,
          actions_completed: approved ? 1 : 0,
          pending_approvals: approved ? 0 : 1,
          failed_actions: 0,
          time_saved_minutes: 10,
        }
      : path === "/api/v1/events"
        ? { items: [event], next_cursor: null }
        : path === "/api/v1/events/event-1"
          ? {
              ...event,
              source: "manual",
              latest_plan: {
                id: "plan-1",
                objective: "Prepare the Lisbon trip",
                status: approved ? "completed" : "waiting_approval",
                action_count: 1,
                completed_actions: approved ? 1 : 0,
                pending_actions: approved ? 0 : 1,
              },
            }
          : path.endsWith("/timeline")
            ? {
                items: [
                  {
                    id: "audit-1",
                    life_event_id: "event-1",
                    plan_id: "plan-1",
                    action_id: "action-1",
                    event_name: approved ? "action_completed" : "approval_requested",
                    actor_type: "system",
                    request_id: null,
                    payload: {},
                    created_at: now,
                  },
                ],
                next_cursor: null,
              }
            : path === "/api/v1/plans/plan-1"
              ? plan(approved)
              : path === "/api/v1/standing-orders" && request.method() === "GET"
                ? []
                : path === "/api/v1/standing-orders"
                  ? {
                      id: "order-1",
                      instruction: "Prepare my flights",
                      enabled: true,
                      compilation_status: "compiled",
                      compiled_rule: null,
                      version: 1,
                      last_error: null,
                      created_at: now,
                      updated_at: now,
                    }
                  : path === "/api/v1/events/manual"
                    ? {
                        id: "event-1",
                        raw_event_id: "raw-1",
                        type: "travel_booked",
                        status: "normalized",
                        is_duplicate: false,
                      }
                    : path === "/api/v1/approvals" && request.method() === "GET"
                      ? approved
                        ? []
                        : [
                            {
                              id: "approval-1",
                              action_id: "action-1",
                              decision: null,
                              expires_at: "2026-07-16T10:00:00Z",
                              decided_at: null,
                              decided_by_user_id: null,
                              action: plan(false).actions[0],
                            },
                          ]
                      : path.endsWith("/approve")
                        ? ((approved = true),
                          {
                            id: "approval-1",
                            action_id: "action-1",
                            decision: "approved",
                            expires_at: "2026-07-16T10:00:00Z",
                            decided_at: now,
                            decided_by_user_id: "user-1",
                            action: plan(true).actions[0],
                          })
                        : {};
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
}

test("critical FlowPilot journey uses isolated providers", async ({ page }) => {
  await page.setExtraHTTPHeaders({ "x-flowpilot-e2e": "1" });
  await useDemoApi(page);
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in to your workspace" })).toBeVisible();
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Your day" })).toBeVisible();
  await page.goto("/dashboard/standing-orders");
  await page.getByLabel("What should FlowPilot do?").fill("Prepare my flights");
  await page.getByRole("button", { name: "Save automation" }).click();
  await expect(page.getByText("Prepare my flights")).toBeVisible();
  await page.goto("/events/new");
  await page.getByLabel("What happened?").fill("Flight AA123 to Lisbon is confirmed");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("status")).toContainText("Ready");
  await page.goto("/dashboard/events/event-1");
  await expect(page.getByText("Prepare the Lisbon trip")).toBeVisible();
  await page.goto("/dashboard/approvals");
  await page.getByRole("button", { name: "Allow" }).click();
  await page.getByRole("button", { name: "Allow action" }).click();
  await expect(page.getByText("Nothing to review")).toBeVisible();
  await page.goto("/dashboard/events/event-1");
  await expect(page.getByText("action completed")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("heading", { name: "Flight AA123 to Lisbon" })).toBeVisible();
});
