import { NextResponse, type NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
    // L0 Local Auth: Simple cookie check or just allow all for now if we relying on client-side
    // But verify instructions: "Redirect ALL protected pages to /login if no valid session"

    // For L0, since login page sets localStorage (client-side), middleware (server-side) 
    // cannot verify auth unless we move to cookies.
    // Changing login to set cookie is better.
    // BUT, for now, let's implement a "public path" check so we don't accidentally block login.

    const publicPaths = ['/login', '/signup', '/onboarding', '/auth/desktop', '/api/auth/login', '/api/auth/register'];
    const path = request.nextUrl.pathname;

    if (publicPaths.some(p => path.startsWith(p))) {
        return NextResponse.next();
    }

    // If we want to enforce auth in middleware, we need a cookie.
    // Let's assume the 'k24_auth' cookie will be present.
    const token = request.cookies.get('k24_token');

    if (!token && !path.startsWith('/_next') && !path.startsWith('/static')) {
        // Redirect to login
        const loginUrl = new URL('/login', request.url);
        return NextResponse.redirect(loginUrl);
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - public files
         */
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
