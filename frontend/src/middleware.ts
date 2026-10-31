import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = [
  "/feed",
  "/profile",
  "/notifications",
  "/messages",
  "/friends",
  "/admin",
  "/settings",
];

const AUTH_PAGES = ["/login", "/register", "/forgot-password"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasRefreshToken = request.cookies.has("refresh_token");
  const userRole = request.cookies.get("user_role")?.value;
  const isAdmin = userRole === "admin";

  // 1. Root Landing Page: If already authenticated, redirect to destination
  if (pathname === "/" && hasRefreshToken) {
    const dest = isAdmin ? "/admin" : "/feed";
    return NextResponse.redirect(new URL(dest, request.url));
  }

  // 2. Redirect unauthenticated users from protected routes to /login
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  if (isProtected && !hasRefreshToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 3. Admin Route Protection: If non-admin attempts /admin, redirect to /feed
  if (pathname.startsWith("/admin") && hasRefreshToken && userRole && !isAdmin) {
    return NextResponse.redirect(new URL("/feed", request.url));
  }

  // 4. Redirect already authenticated users from auth pages to their destination
  const isAuthPage = AUTH_PAGES.some(
    (page) => pathname === page || pathname.startsWith(`${page}/`)
  );

  if (isAuthPage && hasRefreshToken) {
    const dest = isAdmin ? "/admin" : "/feed";
    return NextResponse.redirect(new URL(dest, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/feed/:path*",
    "/profile/:path*",
    "/notifications/:path*",
    "/messages/:path*",
    "/friends/:path*",
    "/admin",
    "/admin/:path*",
    "/settings/:path*",
    "/login",
    "/register",
    "/forgot-password",
  ],
};
