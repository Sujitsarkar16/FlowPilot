import { Bell } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { UserMenu } from "@/components/layout/user-menu";

export function Topbar() {
  return (
    <header className="flex min-h-[4.5rem] items-center justify-between border-b border-slate-200/80 bg-white px-4 sm:px-6 lg:px-8">
      <Link
        aria-label="FlowPilot dashboard home"
        className="flex items-center md:hidden"
        href="/dashboard"
      >
        <Image
          alt="FlowPilot"
          className="h-32 w-32 object-contain"
          height={48}
          priority
          src="/flowpilot-logo.png"
          width={48}
        />
      </Link>
      <p className="hidden items-center text-sm font-medium text-slate-600 md:flex">
        <span aria-hidden="true" className="mr-2 h-2 w-2 rounded-full bg-emerald-500" />
        Workspace protected
      </p>
      <div className="flex items-center gap-2">
        <button
          aria-label="View notifications"
          className="relative rounded-lg p-2 text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          type="button"
        >
          <Bell aria-hidden="true" size={20} />
          <span
            aria-hidden="true"
            className="absolute right-1 top-1 h-2 w-2 rounded-full bg-indigo-600"
          />
        </button>
        <UserMenu />
      </div>
    </header>
  );
}
