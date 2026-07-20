import { type NextRequest, NextResponse } from "next/server";

export async function middleware(request: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return redirectToLogin(request, "configuration");
  const cookie = request.headers.get("cookie");
  if (!cookie) return redirectToLogin(request);

  try {
    const response = await fetch(`${apiUrl}/api/v1/auth/session`, {
      headers: { Cookie: cookie },
      cache: "no-store",
    });
    if (!response.ok) return redirectToLogin(request);
  } catch {
    return redirectToLogin(request, "configuration");
  }

  const response = NextResponse.next();
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

function redirectToLogin(request: NextRequest, error?: string) {
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  url.searchParams.set("returnTo", request.nextUrl.pathname);
  if (error) url.searchParams.set("error", error);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/dashboard/:path*", "/events/:path*"],
};
