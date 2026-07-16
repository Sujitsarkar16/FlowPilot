import { Auth0Client } from "@auth0/nextjs-auth0/server";
import { NextResponse } from "next/server";

/**
 * Auth0 client for the whole app. The `audience` is required so Auth0 issues a
 * JWT access token (not an opaque token) that the FastAPI backend can verify
 * against Auth0's JWKS. `offline_access` lets the SDK refresh tokens silently.
 */
export const auth0 = new Auth0Client({
  authorizationParameters: {
    scope: "openid profile email offline_access",
    audience: process.env.AUTH0_AUDIENCE,
  },
  // Surface Auth0 errors (e.g. invalid audience) as a readable message on /login
  // instead of a raw 500 from the callback.
  async onCallback(error, context) {
    const baseUrl = context.appBaseUrl ?? process.env.APP_BASE_URL ?? "http://localhost:3000";
    if (error) {
      const url = new URL("/login", baseUrl);
      url.searchParams.set("error", error.message);
      return NextResponse.redirect(url);
    }
    return NextResponse.redirect(new URL(context.returnTo ?? "/dashboard", baseUrl));
  },
});
