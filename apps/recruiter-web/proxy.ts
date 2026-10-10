import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE = "__Host-medlivo-team";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname === "/team" ||
    pathname.startsWith("/api/team/") ||
    pathname.startsWith("/_next/") ||
    pathname === "/favicon.ico"
  ) {
    return NextResponse.next();
  }

  if (!request.cookies.get(SESSION_COOKIE)?.value) {
    const url = request.nextUrl.clone();
    url.pathname = "/team";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/jobs/:path*",
    "/candidates/:path*",
    "/funnel/:path*",
    "/manager/:path*",
    "/admin/:path*",
    "/executive/:path*",
  ],
};
