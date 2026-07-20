"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { createClient } from "@/lib/supabase/client";

type AuthMode = "sign-in" | "sign-up";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const isSignUp = mode === "sign-up";
  const requestedPath = searchParams?.get("returnTo") ?? "/dashboard";
  const returnTo = requestedPath.startsWith("/") && !requestedPath.startsWith("//") ? requestedPath : "/dashboard";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    try {
      const supabase = createClient();
      const result = isSignUp
        ? await supabase.auth.signUp({
            email,
            password,
            options: { emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(returnTo)}` },
          })
        : await supabase.auth.signInWithPassword({ email, password });
      if (result.error) throw result.error;
      if (isSignUp && !result.data.session) {
        setMessage("Check your email to confirm your account, then sign in.");
        return;
      }
      window.location.assign(returnTo);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to authenticate.");
    } finally {
      setSubmitting(false);
    }
  }

  async function signInWithGoogle() {
    setSubmitting(true);
    setMessage("");
    try {
      const { data, error } = await createClient().auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(returnTo)}` },
      });
      if (error || !data.url) throw error ?? new Error("Google sign-in could not be started.");
      window.location.assign(data.url);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start Google sign-in.");
      setSubmitting(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <label className="block text-sm font-medium text-slate-700" htmlFor="email">
        Email
        <input
          autoComplete="email"
          className="mt-1.5 h-11 w-full rounded-lg border border-slate-300 px-3 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          id="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
      </label>
      <label className="block text-sm font-medium text-slate-700" htmlFor="password">
        Password
        <input
          autoComplete={isSignUp ? "new-password" : "current-password"}
          className="mt-1.5 h-11 w-full rounded-lg border border-slate-300 px-3 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          id="password"
          minLength={8}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      {message ? <p className="text-sm text-rose-600" role="alert">{message}</p> : null}
      <button
        className="flex h-11 w-full items-center justify-center rounded-lg bg-indigo-600 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
        disabled={submitting}
        type="submit"
      >
        {submitting ? "Please wait…" : isSignUp ? "Create account" : "Sign in"}
      </button>
      <button
        className="flex h-11 w-full items-center justify-center rounded-lg border border-slate-300 bg-white text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
        disabled={submitting}
        onClick={signInWithGoogle}
        type="button"
      >
        Continue with Google
      </button>
      <p className="text-center text-sm text-slate-500">
        {isSignUp ? "Already have an account?" : "Need an account?"}{" "}
        <Link className="font-semibold text-indigo-600 hover:text-indigo-500" href={isSignUp ? "/login" : "/sign-up"}>
          {isSignUp ? "Sign in" : "Sign up"}
        </Link>
      </p>
    </form>
  );
}
