"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { activeNavigationHref, dashboardNavigation } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/button";

export function MobileNav() {
  const activeHref = activeNavigationHref(usePathname());
  return (
    <nav
      aria-label="Primary navigation"
      className="fixed inset-x-0 bottom-0 z-40 flex gap-1 overflow-x-auto border-t border-slate-200 bg-white px-2 pb-[env(safe-area-inset-bottom)] shadow-lg md:hidden"
    >
      {dashboardNavigation.map(({ href, icon: Icon, label }) => {
        const current = activeHref === href;
        return (
          <Button
            asChild
            className="h-16 min-w-20 shrink-0 flex-col gap-1 px-2 text-[11px]"
            key={href}
            size="sm"
            style={current ? { backgroundColor: "#4f46e5", color: "#fff" } : undefined}
            variant={current ? "default" : "ghost"}
          >
            <Link aria-current={current ? "page" : undefined} href={href}>
              <Icon aria-hidden="true" size={18} />
              <span className="whitespace-nowrap">{label}</span>
            </Link>
          </Button>
        );
      })}
    </nav>
  );
}
