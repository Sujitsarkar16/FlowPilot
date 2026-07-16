import * as axe from "axe-core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/login/page";
import { ApprovalsManager } from "@/features/approvals/approvals-manager";
import { ConnectionsManager } from "@/features/connections/connections-manager";
import { EventDetail } from "@/features/events/event-detail";
import { EventsList } from "@/features/events/events-list";
import { LifeFeed } from "@/features/feed/life-feed";
import { AutonomyManager } from "@/features/autonomy/autonomy-manager";
import { mockApproval, mockEvent, mockPlan } from "@/tests/mocks/data";

const api = vi.hoisted(() => ({ listPendingApprovals: vi.fn(), listConnections: vi.fn(), getEvent: vi.fn(), getEventTimeline: vi.fn(), getPlan: vi.fn(), getDashboardSummary: vi.fn(), listEvents: vi.fn(), getPreferences: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ api }));
vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard/events", useRouter: () => ({ replace: vi.fn() }), useSearchParams: () => new URLSearchParams() }));

async function expectNoSeriousViolations() {
  const result = await axe.run(document.body, { rules: { "color-contrast": { enabled: false } } });
  expect(result.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""))).toEqual([]);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.listPendingApprovals.mockResolvedValue([mockApproval]); api.listConnections.mockResolvedValue([]);
  api.getEvent.mockResolvedValue(mockEvent); api.getEventTimeline.mockResolvedValue({ items: [], next_cursor: null }); api.getPlan.mockResolvedValue(mockPlan);
  api.getDashboardSummary.mockResolvedValue({ events_today: 1, actions_completed: 0, pending_approvals: 1, failed_actions: 0, time_saved_minutes: 5 });
  api.listEvents.mockResolvedValue({ items: [mockEvent], next_cursor: null });
  api.getPreferences.mockResolvedValue({ autonomy_level: "safe_actions", category_behaviors: {}, daily_message_cap: 10, daily_calendar_cap: 10 });
});

describe("primary screen accessibility", () => {
  it("has no serious axe violations in feed, events, detail, approvals, connections, and settings", async () => {
    render(<><LoginPage /><LifeFeed /><EventsList /><EventDetail eventId="event-1" /><ApprovalsManager /><ConnectionsManager /><AutonomyManager /></>);
    await screen.findByRole("heading", { name: "Life Feed" }); await screen.findByRole("heading", { name: "Events" }); await screen.findByRole("heading", { name: "Approvals" });
    await expectNoSeriousViolations();
  });
});
