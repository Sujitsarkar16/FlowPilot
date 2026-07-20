import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConnectionsManager } from "@/features/connections/connections-manager";
import { api } from "@/lib/api/client";
import type { Connection } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  api: {
    disconnect: vi.fn(),
    listConnections: vi.fn(),
    setupTelegram: vi.fn(),
    startOAuth: vi.fn(),
    testConnection: vi.fn(),
  },
}));

const googleConnection: Connection = {
  id: "connection-google",
  provider: "google",
  provider_account_id: "person@example.com",
  status: "connected",
  scopes: ["gmail.readonly"],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockedApi = vi.mocked(api);

describe("ConnectionsManager", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.listConnections.mockResolvedValue([]);
  });

  it("shows permission disclosures for every supported connector", async () => {
    render(<ConnectionsManager />);
    await screen.findByRole("heading", { name: "Google" });

    expect(screen.getByRole("region", { name: "Available connections" })).toBeVisible();
    expect(screen.getAllByText("FlowPilot can access")).toHaveLength(3);
    expect(screen.getAllByText("No account connected yet")).toHaveLength(3);
    expect(screen.getByText("Read Gmail messages")).toBeVisible();
    expect(screen.getByText("Access public repositories")).toBeVisible();
    expect(screen.getByText("Send messages to the specified chat")).toBeVisible();
  });

  it("submits a Telegram setup without displaying the token afterward", async () => {
    const user = userEvent.setup();
    mockedApi.setupTelegram.mockResolvedValue({ ...googleConnection, provider: "telegram" });
    render(<ConnectionsManager />);
    await screen.findByRole("button", { name: "Connect Telegram" });

    await user.click(screen.getByRole("button", { name: "Connect Telegram" }));
    expect(screen.getByRole("dialog", { name: "Connect Telegram" })).toBeVisible();
    await user.type(screen.getByLabelText("Bot token"), "bot-token-value");
    await user.type(screen.getByLabelText("Destination chat ID"), "12345");
    await user.click(screen.getByRole("button", { name: "Save connection" }));

    await waitFor(() =>
      expect(mockedApi.setupTelegram).toHaveBeenCalledWith({
        bot_token: "bot-token-value",
        chat_id: "12345",
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Telegram connection saved.");
    expect(screen.queryByLabelText("Bot token")).not.toBeInTheDocument();
    expect(screen.queryByText("bot-token-value")).not.toBeInTheDocument();
  });

  it("requires confirmation before disconnecting a connection", async () => {
    const user = userEvent.setup();
    mockedApi.listConnections.mockResolvedValueOnce([googleConnection]).mockResolvedValueOnce([]);
    render(<ConnectionsManager />);
    await screen.findByText("person@example.com");

    await user.click(screen.getByRole("button", { name: "Disconnect" }));
    const confirmDialog = screen.getByRole("dialog", { name: "Disconnect this connection?" });
    expect(confirmDialog).toBeVisible();
    await user.click(within(confirmDialog).getByRole("button", { name: "Disconnect" }));

    await waitFor(() => expect(mockedApi.disconnect).toHaveBeenCalledWith("connection-google"));
    expect(await screen.findByRole("status")).toHaveTextContent("Connection disconnected.");
  });
});
