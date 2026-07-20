import type { ReactNode } from "react";

import { MobileNav } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(224,231,255,0.55),_transparent_30%),#f8fafc] md:flex">
      <Sidebar />
      <div className="min-w-0 flex-1 pb-16 md:pb-0">
        <Topbar />
        <div className="dashboard-content">{children}</div>
      </div>
      <MobileNav />
    </div>
  );
}
