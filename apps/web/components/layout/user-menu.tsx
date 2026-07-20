"use client";

import Link from "next/link";
import { LogOut, Settings, UserRound } from "lucide-react";
import { useState } from "react";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
      if (apiUrl)
        await fetch(`${apiUrl}/api/v1/auth/logout`, { method: "POST", credentials: "include" });
    } finally {
      window.location.assign("/login");
    }
  }

  return (
    <div className="relative">
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Open user menu"
        className="rounded-md p-2 text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        <UserRound aria-hidden="true" size={20} />
      </button>
      {open ? (
        <div
          aria-label="User menu"
          className="absolute right-0 z-50 mt-2 w-48 rounded-lg border border-slate-200 bg-white p-1.5 shadow-xl shadow-slate-900/10"
          role="menu"
        >
          <Link
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            href="/dashboard/settings"
            onClick={() => setOpen(false)}
            role="menuitem"
          >
            <Settings aria-hidden="true" size={16} />
            Account settings
          </Link>
          <div className="my-1 border-t border-slate-100" />
          <button
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-60"
            disabled={signingOut}
            onClick={signOut}
            role="menuitem"
            type="button"
          >
            <LogOut aria-hidden="true" size={16} />
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
