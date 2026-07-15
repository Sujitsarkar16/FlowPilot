import { Bell } from "lucide-react";

import { UserMenu } from "@/components/layout/user-menu";

export function Topbar() {
  return (
    <header className="flex min-h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <p className="text-sm text-slate-600">
        <span
          aria-hidden="true"
          className="mr-2 inline-block h-2 w-2 rounded-full bg-emerald-500"
        />
        Workspace protected
      </p>
      <div className="flex items-center gap-2">
        <button
          aria-label="View notifications"
          className="relative rounded-md p-2 text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
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
