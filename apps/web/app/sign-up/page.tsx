import { Suspense } from "react";

import { AuthForm } from "@/components/auth/auth-form";

export default function SignUpPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white px-8 py-9 shadow-sm">
        <div className="mb-7 text-center">
          <span className="text-lg font-semibold text-slate-900">FlowPilot</span>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">
            Create your account
          </h1>
        </div>
        <Suspense fallback={<p className="text-center text-sm text-slate-500">Loading…</p>}>
          <AuthForm mode="sign-up" />
        </Suspense>
      </section>
    </main>
  );
}
