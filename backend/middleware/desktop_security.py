"""
Desktop Token Security Middleware

This middleware validates that API requests come from the authorized
K24 desktop application using a session-specific token.

Security Model:
1. Tauri app generates unique session token on each launch
2. Backend receives token via --token command line argument
3. All API requests must include X-Desktop-Token header
4. Requests without valid token are rejected (403 Forbidden)

This prevents:
- Direct access to localhost:8000 from browsers
- Unauthorized scripts calling the API
- Session hijacking between app restarts
"""

import os
import logging
from typing import List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Environment variables for desktop mode
DESKTOP_MODE = os.getenv("DESKTOP_MODE", "false").lower() == "true"
DESKTOP_TOKEN = os.getenv("DESKTOP_TOKEN", "")

# Public endpoints that don't require desktop token
# (health checks, metrics, etc.)
PUBLIC_ENDPOINTS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
]


class DesktopSecurityMiddleware(BaseHTTPMiddleware):
    """
    Validates X-Desktop-Token header on all requests when running in desktop mode.
    
    Configuration via environment variables:
    - DESKTOP_MODE=true - Enable desktop token validation
    - DESKTOP_TOKEN=<uuid> - The expected session token
    """
    
    def __init__(self, app, public_endpoints: Optional[List[str]] = None):
        super().__init__(app)
        self.public_endpoints = public_endpoints or PUBLIC_ENDPOINTS
        
        if DESKTOP_MODE:
            if DESKTOP_TOKEN:
                logger.info("Desktop security enabled with session token")
            else:
                logger.warning("Desktop mode enabled but no token configured!")
        else:
            logger.info("Running in development mode (no token validation)")
    
    async def dispatch(self, request: Request, call_next):
        # Skip validation if not in desktop mode
        if not DESKTOP_MODE:
            return await call_next(request)
        
        # Skip validation for public endpoints
        path = request.url.path
        if any(path.startswith(endpoint) for endpoint in self.public_endpoints):
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Validate desktop token
        provided_token = request.headers.get("X-Desktop-Token", "")
        
        if not provided_token:
            logger.warning(f"Missing X-Desktop-Token header for {path}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": "Desktop token required. Use K24 application to access this API."
                }
            )
        
        if provided_token != DESKTOP_TOKEN:
            logger.warning(f"Invalid X-Desktop-Token for {path}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden", 
                    "detail": "Invalid desktop token. Session may have expired."
                }
            )
        
        # Token valid, proceed with request
        return await call_next(request)


def configure_desktop_mode(port: int = 8000, token: str = ""):
    """
    Configure desktop mode settings.
    Called from command line arguments when launched by Tauri.
    
    Usage in main.py:
        if '--desktop-mode' in sys.argv:
            configure_desktop_mode(
                port=int(sys.argv[sys.argv.index('--port') + 1]),
                token=sys.argv[sys.argv.index('--token') + 1]
            )
    """
    global DESKTOP_MODE, DESKTOP_TOKEN
    
    DESKTOP_MODE = True
    DESKTOP_TOKEN = token
    
    # Update environment for child processes
    os.environ["DESKTOP_MODE"] = "true"
    os.environ["DESKTOP_TOKEN"] = token
    
    logger.info(f"Desktop mode configured: port={port}")


def is_desktop_mode() -> bool:
    """Check if running in desktop mode"""
    return DESKTOP_MODE


def get_desktop_token() -> str:
    """Get current desktop token (for testing)"""
    return DESKTOP_TOKEN if DESKTOP_MODE else ""
