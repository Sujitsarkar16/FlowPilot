import Image from "next/image";
import { Suspense } from "react";

import { AuthForm } from "@/components/auth/auth-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white px-8 py-9 shadow-sm">
        <div className="mb-7 flex flex-col items-center text-center">
          <Image
            alt="FlowPilot"
            className="h-16 w-16 object-contain"
            height={64}
            priority
            src="/flowpilot-logo.png"
            width={64}
          />
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">
            Sign in to your workspace
          </h1>
        </div>
        <Suspense fallback={<p className="text-center text-sm text-slate-500">Loading…</p>}>
          <AuthForm mode="sign-in" />
        </Suspense>
      </section>
    </main>
  );
}
