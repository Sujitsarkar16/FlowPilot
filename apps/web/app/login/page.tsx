"use client";

import { FormEvent, useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const callbackError = new URLSearchParams(window.location.search).get("error");
    if (callbackError === "auth_not_configured") setError("Authentication is not configured yet.");
    if (callbackError === "callback_failed")
      setError("We could not finish that sign-in. Please try again.");
  }, []);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    try {
      const { error: signInError } = await createClient().auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback?next=/dashboard` },
      });
      if (signInError) throw signInError;
      setStatus("sent");
    } catch {
      setError("We could not send that sign-in link. Check the address and try again.");
      setStatus("idle");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--canvas)] p-6">
      <section className="w-full max-w-md rounded-2xl border border-[var(--line)] bg-white p-8 shadow-[var(--shadow)]">
        <p className="text-sm font-semibold text-[var(--accent)]">pulseOS</p>
        <h1 className="mt-3 text-3xl font-semibold text-[var(--ink)]">Sign in to your workspace</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          We will email a secure, one-time sign-in link.
        </p>
        <form className="mt-7 space-y-4" onSubmit={signIn}>
          <label className="block text-sm font-medium text-[var(--ink)]" htmlFor="email">
            Email address
          </label>
          <input
            className="h-11 w-full rounded-md border border-[var(--line-strong)] px-3 text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          {error && (
            <p className="text-sm text-[var(--red)]" role="alert">
              {error}
            </p>
          )}
          {status === "sent" && (
            <p className="text-sm text-[var(--green)]" role="status">
              Check your inbox for the sign-in link.
            </p>
          )}
          <button
            className="h-11 w-full rounded-md bg-[var(--accent)] font-medium text-white hover:bg-[var(--accent-dark)] disabled:opacity-60"
            disabled={status === "loading" || status === "sent"}
            type="submit"
          >
            {status === "loading"
              ? "Sending link…"
              : status === "sent"
                ? "Link sent"
                : "Email me a sign-in link"}
          </button>
        </form>
      </section>
    </main>
  );
}
