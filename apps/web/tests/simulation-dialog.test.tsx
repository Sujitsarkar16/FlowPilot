import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SimulationDialog } from "@/features/standing-orders/simulation-dialog";

describe("SimulationDialog", () => {
  it("labels simulation as non-executing and displays proposed action risk", () => {
    render(
      <SimulationDialog
        busy={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        open
        result={{
          event_type: "travel_booked",
          matched: true,
          proposed_actions: [{ action_type: "travel.notify_family", connector: "telegram", input: {}, risk_level: "yellow", approval_mode: "approval_required" }],
          warnings: ["The message will require approval."],
        }}
      />,
    );
    expect(screen.getByText(/nothing is executed/i)).toBeInTheDocument();
    expect(screen.getByText(/this rule matches/i)).toBeInTheDocument();
    expect(screen.getByText(/travel notify family/i)).toBeInTheDocument();
    expect(screen.getByText("Review required")).toBeInTheDocument();
  });
});
