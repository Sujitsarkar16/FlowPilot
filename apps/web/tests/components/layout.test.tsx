import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { usePathname } = vi.hoisted(() => ({ usePathname: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname }));

import { MobileNav } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

afterEach(cleanup);

describe("dashboard navigation", () => {
  it("marks the selected desktop route and exposes every route as a link", () => {
    usePathname.mockReturnValue("/dashboard/approvals");
    render(<Sidebar />);
    expect(screen.getByRole("link", { name: "Approvals" })).toHaveAttribute("aria-current", "page");
    for (const label of [
      "Home",
      "Events",
      "Standing Orders",
      "Approvals",
      "Connections",
      "Settings",
    ])
      expect(screen.getByRole("link", { name: label })).toBeVisible();
  });

  it("marks the selected mobile route and provides accessible controls", () => {
    usePathname.mockReturnValue("/dashboard/events");
    render(
      <>
        <MobileNav />
        <Topbar />
      </>,
    );
    expect(screen.getByRole("link", { name: "Events" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "View notifications" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Open user menu" })).toBeVisible();
  });
});
