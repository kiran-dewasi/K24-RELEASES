
from fastapi import Security, HTTPException, status, Request
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY_NAME = "x-api-key"
API_KEY = os.getenv("API_KEY", "k24-secret-key-123")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")


def get_tenant_id(request: Request) -> str:
    """
    Resolve tenant_id from the Bearer JWT token in the Authorization header.

    This is the single source of truth for tenant resolution on all
    x-api-key authenticated routes (dashboard, reports, vouchers, etc.).

    Resolution order:
      1. JWT Bearer token "tenant_id" claim (authoritative, set at login)
      2. Local SQLite users table (cache/fallback for backward compat)
      3. First non-default tenant found in Ledger data (data-derived fallback)

    Never returns "default" or any hardcoded fallback — raises 401 if no
    valid tenant can be resolved.
    """
    from jose import jwt, JWTError

    # ── Step 1: Try Bearer token (JWT claim — most authoritative) ──────────
    auth_header: Optional[str] = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        try:
            secret = os.getenv("JWT_SECRET_KEY")
            algo   = os.getenv("JWT_ALGORITHM", "HS256")
            if secret:
                payload = jwt.decode(token, secret, algorithms=[algo])
                tenant_from_jwt = payload.get("tenant_id")
                if tenant_from_jwt and tenant_from_jwt not in ("", "default", "offline-default"):
                    return tenant_from_jwt.upper()  # Always uppercase
        except JWTError:
            pass  # Fall through to session store

    # ── Step 1.5: Persisted Session File ────────────────────────────────────
    try:
        from session_store import get_tenant_id_from_session
        tid = get_tenant_id_from_session()
        if tid and tid not in ("", "default", "offline-default"):
            return tid.upper()
    except Exception as e:
        logger.debug(f"session_store lookup failed: {e}")

    # ── Step 2: Local SQLite users table (cache, populated at login) ───────
    try:
        from database import SessionLocal, User, Ledger

        db = SessionLocal()
        try:
            user = (
                db.query(User)
                .filter(
                    User.is_active == True,
                    User.tenant_id != None,
                    User.tenant_id != "default",
                    User.tenant_id != "offline-default"
                )
                .order_by(User.last_login.desc().nullslast())
                .first()
            )
            if user and user.tenant_id:
                logger.debug("get_tenant_id: resolved from local users table (cache)")
                return user.tenant_id

            # ── Step 3: Derive from synced data (last resort) ───────────────
            row = (
                db.query(Ledger.tenant_id)
                .filter(
                    Ledger.tenant_id != None,
                    Ledger.tenant_id != "default"
                )
                .first()
            )
            if row:
                logger.warning(
                    "get_tenant_id: No valid user in DB — derived from ledger data."
                )
                return row[0]

        finally:
            db.close()

    except Exception as e:
        logger.debug(f"get_tenant_id DB lookup error: {e}")

    # ── No tenant found — raise 401 ─────────────────────────────────────────
    logger.error(
        "get_tenant_id: Could not resolve tenant_id from JWT or DB. "
        "User must log in via Supabase first."
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not resolve tenant identity. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_current_user():
    """
    Optional current-user dependency for routes that accept both
    authenticated and unauthenticated requests.

    The desktop backend uses x-api-key authentication, not bearer tokens,
    so there is no JWT-based user lookup. This function always returns None,
    satisfying Optional[User] type hints in routers like customers.py
    without raising errors.
    """
    return None
