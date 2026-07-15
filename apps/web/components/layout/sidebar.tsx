"use client";

import { CalendarDays, CheckSquare, Home, ListTodo, Plug, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

export const dashboardNavigation = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/dashboard/events", label: "Events", icon: CalendarDays },
  { href: "/dashboard/standing-orders", label: "Standing Orders", icon: ListTodo },
  { href: "/dashboard/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/dashboard/connections", label: "Connections", icon: Plug },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
] as const;

export function isCurrentRoute(pathname: string, href: string) {
  return href === "/dashboard"
    ? pathname === href
    : pathname.startsWith(`${href}/`) || pathname === href;
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex">
      <Link
        aria-label="FlowPilot dashboard home"
        className="px-3 py-3 text-xl font-bold text-slate-950"
        href="/dashboard"
      >
        pulse<span className="text-indigo-600">OS</span>
      </Link>
      <p className="px-3 pb-5 text-xs text-slate-500">Personal control centre</p>
      <nav aria-label="Primary navigation" className="space-y-1">
        {dashboardNavigation.map(({ href, icon: Icon, label }) => {
          const current = isCurrentRoute(pathname, href);
          return (
            <Link
              aria-current={current ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                current ? "bg-indigo-50 text-indigo-700" : "text-slate-700 hover:bg-slate-100",
              )}
              href={href}
              key={href}
            >
              <Icon aria-hidden="true" size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
