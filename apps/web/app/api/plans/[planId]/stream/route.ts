import { type NextRequest, NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, { params }: { params: Promise<{ planId: string }> }) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return NextResponse.json({ detail: "The API URL is not configured." }, { status: 503 });

  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  const { data: sessionData } = await supabase.auth.getSession();
  if (!claimsData?.claims || !sessionData.session?.access_token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { planId } = await params;
  const upstream = await fetch(
    `${apiUrl.replace(/\/$/, "")}/api/v1/plans/${encodeURIComponent(planId)}/stream`,
    {
      headers: { Accept: "text/event-stream", Authorization: `Bearer ${sessionData.session.access_token}` },
      cache: "no-store",
      signal: request.signal,
    },
  );
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Cache-Control": "no-cache, no-store",
      "Content-Type": upstream.headers.get("Content-Type") ?? "text/event-stream",
      "X-Accel-Buffering": "no",
    },
  });
}
