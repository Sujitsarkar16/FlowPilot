import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ list: vi.fn(), approve: vi.fn(), reject: vi.fn() }));
vi.mock("@/lib/api/client", () => ({
  api: {
    listPendingApprovals: apiMocks.list,
    approveApproval: apiMocks.approve,
    rejectApproval: apiMocks.reject,
  },
}));

import { ApprovalsManager } from "@/features/approvals/approvals-manager";

const approval = {
  id: "approval-1", action_id: "action-1", decision: null, expires_at: "2026-01-02T00:00:00Z", decided_at: null, decided_by_user_id: null,
  action: { id: "action-1", action_type: "travel.send_family_message", connector: "telegram", input: { message: "ready" }, status: "waiting_approval", risk_level: "red", requires_approval: true, policy_reason: "red_requires_approval", completed_at: null },
};

describe("ApprovalsManager", () => {
  beforeEach(() => {
    apiMocks.list.mockResolvedValue([approval]);
    apiMocks.approve.mockResolvedValue({ ...approval, decision: "approved" });
  });

  it("shows action context and requires confirmation before a high-risk approval", async () => {
    const user = userEvent.setup();
    render(<ApprovalsManager />);
    expect(await screen.findByText("travel send family message")).toBeInTheDocument();
    expect(screen.getByText("High risk")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(screen.getByRole("dialog", { name: "Confirm high-risk action" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Approve action" }));

    await waitFor(() => expect(apiMocks.approve).toHaveBeenCalledWith("approval-1"));
    expect(screen.queryByText("travel send family message")).not.toBeInTheDocument();
  });
});
