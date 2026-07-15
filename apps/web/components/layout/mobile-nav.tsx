"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { dashboardNavigation, isCurrentRoute } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary navigation"
      className="fixed inset-x-0 bottom-0 z-40 flex border-t border-slate-200 bg-white px-1 pb-[env(safe-area-inset-bottom)] shadow-lg md:hidden"
    >
      {dashboardNavigation.map(({ href, icon: Icon, label }) => {
        const current = isCurrentRoute(pathname, href);
        return (
          <Link
            aria-current={current ? "page" : undefined}
            className={cn(
              "flex min-h-14 flex-1 flex-col items-center justify-center gap-1 rounded-sm text-[10px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500",
              current ? "text-indigo-700" : "text-slate-600",
            )}
            href={href}
            key={href}
          >
            <Icon aria-hidden="true" size={18} />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
