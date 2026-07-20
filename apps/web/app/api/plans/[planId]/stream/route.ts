import { type NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ planId: string }> },
) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl)
    return NextResponse.json({ detail: "The API URL is not configured." }, { status: 503 });

  const { planId } = await params;
  const upstream = await fetch(
    `${apiUrl.replace(/\/$/, "")}/api/v1/plans/${encodeURIComponent(planId)}/stream`,
    {
      headers: {
        Accept: "text/event-stream",
        Cookie: request.headers.get("cookie") ?? "",
      },
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
