
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
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


def get_tenant_id() -> str:
    """
    Single source of truth for tenant_id resolution.

    Resolution order:
      1. Local SQLite User table — populated from Supabase at login
         (this IS the Supabase tenant_id, synced during auth flow)
      2. First non-default tenant found in Ledger data
      3. Fallback to "default" with a warning

    This function is used as a FastAPI Depends() across all routers
    that use x-api-key auth (dashboard, reports, vouchers, etc.)
    """
    from backend.database import SessionLocal, User, Ledger

    try:
        db = SessionLocal()
        try:
            # Primary: get from the logged-in User (synced from Supabase at login)
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
                return user.tenant_id

            # Fallback: derive from actual data in the DB
            # (handles case where user table has "default" but data was synced correctly)
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
                    f"get_tenant_id: User table has no valid tenant, "
                    f"deriving from data: {row[0]}"
                )
                return row[0]

        finally:
            db.close()

    except Exception as e:
        logger.debug(f"get_tenant_id error: {e}")

    logger.warning(
        "get_tenant_id: Could not resolve tenant_id from DB. "
        "Ensure user has logged in via Supabase."
    )
    return "default"
