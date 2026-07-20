import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { origin, searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const candidate = searchParams.get("next") ?? "/dashboard";
  const next = candidate.startsWith("/") && !candidate.startsWith("//") ? candidate : "/dashboard";

  if (code) {
    try {
      const supabase = await createClient();
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) return NextResponse.redirect(new URL(next, origin));
    } catch {
      // Fall through to the login page without exposing provider details.
    }
  }
  return NextResponse.redirect(new URL("/login?error=oauth", origin));
}
