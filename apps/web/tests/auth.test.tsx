import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LoginPage from "@/app/login/page";

describe("login", () => {
  it("links to Auth0 universal login for sign in and sign up", () => {
    render(<LoginPage />);
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/auth/login?returnTo=%2Fdashboard",
    );
    expect(screen.getByRole("link", { name: "Create an account" })).toHaveAttribute(
      "href",
      "/auth/login?screen_hint=signup&returnTo=%2Fdashboard",
    );
  });
});
