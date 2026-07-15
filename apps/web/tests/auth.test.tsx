import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const signInWithOtp = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signInWithOtp } }),
}));

import LoginPage from "@/app/login/page";

describe("login", () => {
  beforeEach(() => signInWithOtp.mockResolvedValue({ error: null }));

  it("sends a magic link and reports success", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByLabelText("Email address"), "person@example.com");
    await user.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(signInWithOtp).toHaveBeenCalledWith({
      email: "person@example.com",
      options: { emailRedirectTo: "http://localhost:3000/auth/callback?next=/dashboard" },
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Check your inbox");
  });
});
