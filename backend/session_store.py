"""
session_store.py
================

Persistent session store for the desktop backend.

Saves the JWT access_token to a local `.session.json` file on login so that
backend --reload and manual restarts do NOT lose authentication state.

Token is cleared only on explicit logout.

Security notes:
  - File is local-only; never committed (added to .gitignore).
  - File path lives next to the backend entry-point (or APPDATA in packaged mode).
  - No passwords or secrets are stored — only the already-issued JWT.
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("session_store")

# ── Session file location ──────────────────────────────────────────────────────
# In dev mode  → <repo>/backend/.session.json  (sibling of api.py)
# In packaged mode → %APPDATA%/k24/.session.json  (writable user directory)

def _session_file_path() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", Path.home())) / "k24"
    else:
        # Use the directory where this module lives (backend/)
        base = Path(__file__).parent
    return base / ".session.json"


SESSION_FILE: Path = _session_file_path()


# ── Public API ─────────────────────────────────────────────────────────────────

def save_session(access_token: str, tenant_id: Optional[str] = None, username: Optional[str] = None) -> None:
    """
    Persist the JWT access_token (and optional metadata) to .session.json.
    Called immediately after a successful login.
    """
    data = {
        "access_token": access_token,
        "tenant_id": tenant_id,
        "username": username,
    }
    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("✅ Session persisted to %s", SESSION_FILE)
    except Exception as e:
        logger.error("❌ Failed to persist session: %s", e)


def load_session() -> Optional[dict]:
    """
    Load the persisted session from .session.json.
    Returns the parsed dict, or None if no session file exists or it's corrupt.
    """
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        if data.get("access_token"):
            logger.info("📂 Loaded persisted session from %s", SESSION_FILE)
            return data
    except Exception as e:
        logger.warning("⚠️  Could not read session file (%s): %s", SESSION_FILE, e)
    return None


def clear_session() -> None:
    """
    Delete .session.json — called on explicit logout.
    """
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
            logger.info("🗑️  Session cleared (%s deleted)", SESSION_FILE)
    except Exception as e:
        logger.warning("⚠️  Could not clear session file: %s", e)


def get_token_from_session() -> Optional[str]:
    """
    Convenience helper: return just the access_token string, or None.
    """
    session = load_session()
    return session.get("access_token") if session else None


def get_tenant_id_from_session() -> Optional[str]:
    """
    Resolve tenant_id from the persisted JWT payload.

    Resolution order:
      1. Stored `tenant_id` field (set at save time from the JWT claim).
      2. Decode the `access_token` JWT directly and read the `tenant_id` claim.

    Returns None if no session exists or tenant cannot be resolved.
    Never returns "default", "offline-default", or any hardcoded fallback.
    """
    session = load_session()
    if not session:
        return None

    # Fast path: tenant_id was cached directly in the session file
    stored_tid = session.get("tenant_id")
    if stored_tid and stored_tid not in ("", "default", "offline-default"):
        return stored_tid.upper()

    # Fallback: decode the JWT to extract the claim
    token = session.get("access_token")
    if not token:
        return None

    try:
        from jose import jwt, JWTError
        secret = os.getenv("JWT_SECRET_KEY")
        algo   = os.getenv("JWT_ALGORITHM", "HS256")
        if secret:
            payload = jwt.decode(token, secret, algorithms=[algo])
            tid = payload.get("tenant_id")
            if tid and tid not in ("", "default", "offline-default"):
                return tid.upper()
    except Exception as e:
        logger.debug("Could not decode JWT from session file: %s", e)

    return None
