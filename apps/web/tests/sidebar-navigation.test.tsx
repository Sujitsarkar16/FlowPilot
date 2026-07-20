import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Sidebar, activeNavigationHref } from "@/components/layout/sidebar";
import { buttonVariants } from "@/components/ui/button";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));

describe("activeNavigationHref", () => {
  it("selects only the most specific route for nested navigation", () => {
    expect(activeNavigationHref("/dashboard/settings/autonomy")).toBe(
      "/dashboard/settings/autonomy",
    );
    expect(activeNavigationHref("/dashboard/settings")).toBe("/dashboard/settings");
    expect(activeNavigationHref("/dashboard/events/event-1")).toBe("/dashboard/events");
  });
});

describe("shadcn Button", () => {
  it("keeps the primary navigation treatment visible without theme variables", () => {
    expect(buttonVariants({ variant: "default" })).toContain("bg-[#4f46e5]");
    expect(buttonVariants({ variant: "default" })).toContain("text-white");
  });
});

describe("Sidebar", () => {
  it("renders the selected route with visible foreground and background colors", () => {
    render(<Sidebar />);
    const home = screen.getByRole("link", { name: "Home" });
    expect(home).toHaveAttribute("aria-current", "page");
    expect(home).toHaveStyle({ backgroundColor: "rgb(79, 70, 229)", color: "rgb(255, 255, 255)" });
  });
});
