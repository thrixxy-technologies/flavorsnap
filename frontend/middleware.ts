
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  // 1. Session Management: Check for authentication token
  const token = request.cookies.get('auth_token');
  const { pathname } = request.nextUrl;

  // Protect dashboard and settings routes
  if (pathname.startsWith('/dashboard') || pathname.startsWith('/settings')) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // 2. CSRF Protection: Verify Origin/Referer for mutations
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method)) {
    const origin = request.headers.get('origin');
    const referer = request.headers.get('referer');
    const host = request.headers.get('host');

    if (origin && !origin.includes(host!)) {
      return new NextResponse('Invalid Origin', { status: 403 });
    }
  }

  // 3. Security Logging
  console.log(`[ACCESS] ${request.method} ${pathname} - ${new Date().toISOString()}`);

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
