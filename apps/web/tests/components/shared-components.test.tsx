import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { RiskBadge } from "@/components/risk-badge";
import { StatusBadge } from "@/components/status-badge";

const statuses = [
  "draft",
  "policy_checked",
  "running",
  "waiting_approval",
  "completed",
  "partially_completed",
  "failed",
  "cancelled",
  "planned",
  "blocked",
  "approved",
  "queued",
  "rolled_back",
  "not_required",
  "pending",
  "rejected",
  "verified",
];

describe("shared status and feedback components", () => {
  it("renders every frontend status with a readable label", () => {
    render(
      <>
        {statuses.map((status) => (
          <StatusBadge key={status} status={status} />
        ))}
      </>,
    );
    expect(
      screen.getAllByText(
        /Draft|Policy checked|Running|Awaiting approval|Completed|Partially completed|Failed|Cancelled|Planned|Blocked|Approved|Queued|Rolled back|No approval required|Approval pending|Rejected|Verified/,
      ),
    ).toHaveLength(statuses.length);
  });

  it("states risk in text, not only with color", () => {
    render(
      <>
        <RiskBadge risk="green" />
        <RiskBadge risk="yellow" />
        <RiskBadge risk="red" />
      </>,
    );
    expect(screen.getByText("Low risk")).toBeVisible();
    expect(screen.getByText("Review required")).toBeVisible();
    expect(screen.getByText("High risk")).toBeVisible();
  });

  it("makes error details and loading state accessible", () => {
    render(
      <>
        <ErrorState
          error={
            new ApiError({
              kind: "http",
              message: "Invalid request",
              requestId: "req-123",
              detail: "Check email",
            })
          }
        />
        <LoadingSkeleton label="Loading events" />
      </>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Check email");
    expect(screen.getByRole("alert")).toHaveTextContent("Request ID: req-123");
    expect(screen.getByRole("status")).toHaveTextContent("Loading events");
  });

  it("supports keyboard cancellation and destructive confirmation", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        confirmLabel="Delete connection"
        description="This will revoke access."
        destructive
        onCancel={onCancel}
        onConfirm={onConfirm}
        open
        title="Delete connection?"
      />,
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Delete connection?");
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Delete connection" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
