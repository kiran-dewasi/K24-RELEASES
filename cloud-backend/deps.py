"""
Cloud Backend — Shared Dependencies
====================================
Lightweight helpers used as FastAPI Depends() across routers.
"""

import os
import logging
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


def require_internal_key(request: Request) -> bool:
    """
    Guard for internal-only endpoints (billing, admin).
    Must be passed as a FastAPI Depends().
    Compare X-Internal-Key header against BILLING_INTERNAL_KEY env var.
    Fails closed: if key is not configured, all requests are rejected.
    """
    key = os.getenv("BILLING_INTERNAL_KEY")
    provided = request.headers.get("X-Internal-Key")
    if not key or not provided or provided != key:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True
