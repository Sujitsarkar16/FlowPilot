import type { ReactNode } from "react";

import { MobileNav } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-100/70 md:flex">
      <Sidebar />
      <div className="min-w-0 flex-1 pb-16 md:pb-0">
        <Topbar />
        <div className="dashboard-content">{children}</div>
      </div>
      <MobileNav />
    </div>
  );
}
