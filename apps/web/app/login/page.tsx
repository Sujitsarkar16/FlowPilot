"use client";

import { useEffect, useState } from "react";

function safeReturnTo(): string {
  const next = new URLSearchParams(window.location.search).get("returnTo");
  return next?.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export default function LoginPage() {
  const [returnTo, setReturnTo] = useState("/dashboard");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReturnTo(safeReturnTo());
    const callbackError = new URLSearchParams(window.location.search).get("error");
    if (callbackError) setError(decodeURIComponent(callbackError));
  }, []);

  const encoded = encodeURIComponent(returnTo);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <span className="inline-flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              FP
            </span>
            <span className="text-lg font-semibold text-slate-900">FlowPilot</span>
          </span>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white px-8 py-9 shadow-sm">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Sign in to your workspace
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Continue with Auth0 to access your automation control centre.
          </p>

          {error && (
            <p className="mt-5 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          {/* Auth routes require full navigation, so use <a> not next/link. */}
          <a
            className="mt-6 flex h-11 w-full items-center justify-center rounded-lg bg-indigo-600 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            href={`/auth/login?returnTo=${encoded}`}
          >
            Sign in
          </a>
          <a
            className="mt-3 flex h-11 w-full items-center justify-center rounded-lg border border-slate-300 bg-white text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            href={`/auth/login?screen_hint=signup&returnTo=${encoded}`}
          >
            Create an account
          </a>

          <p className="mt-5 text-center text-xs text-slate-400">
            Email, password, and Google sign-in are handled securely by Auth0.
          </p>
        </section>
      </div>
    </main>
  );
}
