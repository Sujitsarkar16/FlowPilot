import { type NextRequest } from "next/server";

import { protectSession } from "@/lib/supabase/middleware";

export function middleware(request: NextRequest) {
  return protectSession(request);
}

export const config = {
  matcher: ["/dashboard/:path*", "/events/:path*"],
};
