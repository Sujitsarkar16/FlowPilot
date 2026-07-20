import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function protectSession(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return redirectToLogin(request, "configuration");

  let response = NextResponse.next({ request });
  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookiesToSet) => {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) return redirectToLogin(request, undefined, response);
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

function redirectToLogin(request: NextRequest, error?: string, response?: NextResponse) {
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  url.searchParams.set("returnTo", request.nextUrl.pathname);
  if (error) url.searchParams.set("error", error);
  const redirect = NextResponse.redirect(url);
  response?.cookies.getAll().forEach((cookie) => redirect.cookies.set(cookie));
  return redirect;
}
