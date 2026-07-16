"use client";

import { CalendarDays, CheckSquare, Home, ListTodo, Plug, Settings, Shield } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";

export const dashboardNavigation = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/dashboard/events", label: "Events", icon: CalendarDays },
  { href: "/dashboard/standing-orders", label: "Standing Orders", icon: ListTodo },
  { href: "/dashboard/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/dashboard/connections", label: "Connections", icon: Plug },
  { href: "/dashboard/settings/autonomy", label: "Autonomy Centre", icon: Shield },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
] as const;

export function activeNavigationHref(pathname: string) {
  return dashboardNavigation
    .filter(({ href }) => pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`)))
    .sort((left, right) => right.href.length - left.href.length)[0]?.href;
}

export function Sidebar() {
  const activeHref = activeNavigationHref(usePathname());
  return (
    <aside className="sticky top-0 hidden h-screen w-72 shrink-0 flex-col border-r border-slate-200/80 bg-white p-5 md:flex">
      <Link aria-label="FlowPilot dashboard home" className="px-3 py-2 text-xl font-bold tracking-tight text-slate-950" href="/dashboard">
        Flow<span className="text-indigo-600">Pilot</span>
      </Link>
      <p className="px-3 pb-6 pt-1 text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Personal control centre</p>
      <nav aria-label="Primary navigation" className="space-y-1">
        {dashboardNavigation.map(({ href, icon: Icon, label }) => {
          const current = activeHref === href;
          return <Button asChild className="w-full justify-start gap-3 rounded-lg px-3" key={href} size="lg" style={current ? { backgroundColor: "#4f46e5", color: "#fff" } : undefined} variant={current ? "default" : "ghost"}>
            <Link aria-current={current ? "page" : undefined} href={href}>
              <Icon aria-hidden="true" size={18} />
              {label}
            </Link>
          </Button>;
        })}
      </nav>
    </aside>
  );
}
