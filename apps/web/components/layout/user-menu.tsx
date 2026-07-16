"use client";

import { useState } from "react";
import { LogOut, UserRound } from "lucide-react";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  function signOut() {
    setSigningOut(true);
    // Full navigation to the Auth0 logout route ends the session and clears cookies.
    window.location.assign("/auth/logout");
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
          className="absolute right-0 z-50 mt-2 w-40 rounded-md border border-slate-200 bg-white p-1 shadow-lg"
          role="menu"
        >
          <button
            className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-60"
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
