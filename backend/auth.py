from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError
import bcrypt
import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import User, get_db

logger = logging.getLogger("auth")

# Security configuration
import os
from dotenv import load_dotenv

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY not set in environment")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET") or ""
if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET not set in environment")

logger.info("[STARTUP] JWT auth module loaded (algorithm: %s)", ALGORITHM)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 365))  # 1 year default for dev

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    # Encode strings to bytes for bcrypt
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    
    try:
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        logger.error("Bcrypt verification error", exc_info=True)
        return False

def get_password_hash(password: str) -> str:
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logger.debug("[AUTH] Validating bearer token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        tenant_id_from_token = payload.get("tenant_id")

        if username is None:
            logger.warning("[AUTH] Token missing 'sub' claim")
            raise credentials_exception

    except ExpiredSignatureError:
        logger.warning("[AUTH] Token has expired")
        raise HTTPException(status_code=401, detail="Token expired")

    except JWTClaimsError:
        logger.warning("[AUTH] Token claims error")
        raise credentials_exception

    except JWTError as e:
        logger.warning("[AUTH] Token decoding failed: %s", type(e).__name__)
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Fallback to lookup by google_api_key (stores Supabase UUID)
        user = db.query(User).filter(
            User.google_api_key == username
        ).first()

    if user is None:
        if tenant_id_from_token:
            return User(
                id=username,
                tenant_id=tenant_id_from_token,
                username=username,
                is_active=True,
                role="viewer"
            )
        logger.warning("[AUTH] User not found in DB for token sub")
        raise credentials_exception

    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_active_user)):
        role_hierarchy = {
            "viewer": 1,
            "accountant": 2,
            "auditor": 3,
            "admin": 4
        }
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user
    return role_checker

def get_current_tenant_id(current_user: User = Depends(get_current_active_user), request: Request = None) -> str:
    """
    Extracts tenant_id from the authenticated user.
    Enforces multi-tenancy isolation.

    Resolution order:
      1. JWT payload → current_user.tenant_id (populated by get_current_user)
      2. Raises 401 — never falls back to "default" or any hardcoded string.
    """
    path = request.url.path if request else "unknown"
    tenant_id = current_user.tenant_id if current_user else None
    logger.debug("[AUTH] Tenant resolved: path=%s tenant=%s", path, tenant_id)

    if not tenant_id or tenant_id in ("default", "offline-default", ""):
        logger.error(
            "[AUTH] get_current_tenant_id: user %s has no valid tenant_id (got %r). "
            "Possible causes: JWT missing tenant_id claim, or user record stale.",
            getattr(current_user, "username", "?"), tenant_id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not resolve tenant identity. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return tenant_id.upper()  # Always uppercase for consistency


def get_optional_current_user(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Returns the authenticated User if a valid Bearer token is provided.
    Returns None if no token or invalid token — does NOT raise 401.

    Use this in endpoints that also accept API-key-only requests (e.g. local desktop app),
    where tenant_id must still be resolved from whoever is actually logged in.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.username == username).first()
    return user  # Could be None if user was deleted

def check_subscription_active(tenant_id: str = Depends(get_current_tenant_id)):
    """
    Dependency to check if the tenant's subscription is active or in a valid trial.
    """
    from services.supabase_service import supabase_http_service
    from datetime import datetime, timezone
    import httpx

    if not supabase_http_service.client or tenant_id in [None, "", "default", "offline-default"]:
        return tenant_id

    try:
        headers = supabase_http_service._get_headers(use_service_key=True)
        response = httpx.get(
            f"{supabase_http_service.url}/rest/v1/tenant_config?tenant_id=eq.{tenant_id}&select=subscription_status,trial_ends_at,trial_credit_limit&limit=1",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                config = data[0]
                status_str = config.get("subscription_status")
                trial_ends_str = config.get("trial_ends_at")

                if status_str == "expired":
                    raise HTTPException(status_code=403, detail="Subscription expired")

                if status_str == "trial" and trial_ends_str:
                    try:
                        trial_ends_dt = datetime.fromisoformat(trial_ends_str.replace('Z', '+00:00'))
                        if datetime.now(timezone.utc) > trial_ends_dt:
                            raise HTTPException(status_code=403, detail="Subscription expired")
                    except ValueError:
                        pass

                # Check trial credit limit
                if status_str == "trial":
                    try:
                        trial_credit_limit = int(config.get("trial_credit_limit") or 90)

                        _supa_url = supabase_http_service.url
                        _headers = supabase_http_service._get_headers(use_service_key=True)

                        # Find active billing cycle
                        _cycle_resp = httpx.get(
                            f"{_supa_url}/rest/v1/billing_cycles"
                            f"?tenant_id=eq.{tenant_id}&status=eq.active"
                            f"&order=created_at.desc&limit=1"
                            f"&select=id",
                            headers=_headers, timeout=5
                        )
                        _credits_used = 0.0
                        if _cycle_resp.status_code == 200 and _cycle_resp.json():
                            _cycle_id = _cycle_resp.json()[0]["id"]
                            _usage_resp = httpx.get(
                                f"{_supa_url}/rest/v1/tenant_usage_summary"
                                f"?tenant_id=eq.{tenant_id}"
                                f"&billing_cycle_id=eq.{_cycle_id}"
                                f"&limit=1&select=credits_used_total",
                                headers=_headers, timeout=5
                            )
                            if _usage_resp.status_code == 200 and _usage_resp.json():
                                _credits_used = float(
                                    _usage_resp.json()[0].get("credits_used_total") or 0
                                )

                        if _credits_used >= trial_credit_limit:
                            raise HTTPException(
                                status_code=403,
                                detail="Trial credit limit reached. Please upgrade."
                            )
                    except HTTPException:
                        raise
                    except Exception:
                        pass  # Fail open on any error
    except httpx.RequestError:
        logger.warning("[AUTH] Subscription check network error", exc_info=True)

    return tenant_id
