import { NextResponse, type NextRequest } from "next/server";
import { auth0 } from "@/lib/auth0";

const protectedPath = (path: string) => path.startsWith("/dashboard");

export async function middleware(request: NextRequest) {
  // Deterministic bypass for end-to-end tests that stub the API directly.
  if (request.headers.get("x-flowpilot-e2e") === "1") return NextResponse.next({ request });

  // Mounts /auth/* (login, logout, callback, profile, access-token) and refreshes rolling sessions.
  const authRes = await auth0.middleware(request);
  if (request.nextUrl.pathname.startsWith("/auth")) return authRes;

  if (protectedPath(request.nextUrl.pathname)) {
    const session = await auth0.getSession(request);
    if (!session) {
      const loginUrl = new URL("/login", request.nextUrl.origin);
      loginUrl.searchParams.set("returnTo", request.nextUrl.pathname + request.nextUrl.search);
      return NextResponse.redirect(loginUrl);
    }
  }

  // The auth middleware response carries refreshed session cookies and must be returned.
  return authRes;
}

export const config = {
  // Broad matcher (excluding static assets) is required for rolling sessions.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
