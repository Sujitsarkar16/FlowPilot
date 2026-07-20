import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ManualEventForm } from "@/features/events/manual-event-form";
import { api } from "@/lib/api/client";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/client", () => ({
  api: { createManualEvent: vi.fn() },
}));

const mockedApi = vi.mocked(api);

describe("ManualEventForm", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits the event and navigates to its detail page", async () => {
    const user = userEvent.setup();
    mockedApi.createManualEvent.mockResolvedValue({
      id: "event-1",
      raw_event_id: "raw-1",
      type: "travel_booked",
      status: "normalized",
      is_duplicate: false,
    });
    render(<ManualEventForm />);

    await user.type(screen.getByLabelText("What happened?"), "Booked a flight to Tokyo");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() =>
      expect(mockedApi.createManualEvent).toHaveBeenCalledWith(
        {
          text: "Booked a flight to Tokyo",
          category_hint: null,
        },
        { timeoutMs: 60_000 },
      ),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard/events/event-1"));
  });

  it("prevents submitting an empty event", async () => {
    const user = userEvent.setup();
    render(<ManualEventForm />);

    const textarea = screen.getByLabelText("What happened?");
    textarea.removeAttribute("required");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(mockedApi.createManualEvent).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Describe the event before submitting.",
    );
  });

  it("fills the textarea from an example", async () => {
    const user = userEvent.setup();
    render(<ManualEventForm />);

    const [example] = screen.getAllByText(/Your flight AA123/);
    await user.click(example);

    expect(screen.getByLabelText("What happened?")).toHaveValue(
      "Your flight AA123 to Tokyo is confirmed, departing Friday at 9:00 AM.",
    );
  });
});
