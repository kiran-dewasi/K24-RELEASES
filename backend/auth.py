from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import User, get_db

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

print(f"[DEBUG SECRET] SECRET_KEY prefix: {str(SECRET_KEY)[:12]}")
print(f"[DEBUG SECRET] ALGORITHM: {ALGORITHM}")
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
        print(f"Bcrypt error: {e}")
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

def create_socket_token(user_id: str, tenant_id: str, license_key: str, expires_days: int = 365) -> str:
    """
    Create a long-lived signed JWT for Socket.IO authentication.
    This prevents impersonation attacks where someone guesses a tenant_id.
    
    Args:
        user_id: The user's ID (from auth system)
        tenant_id: The tenant ID (e.g., TENANT-84F03F7D)
        license_key: The device license key
        expires_days: Token validity in days (default 1 year)
    
    Returns:
        Signed JWT token for socket authentication
    """
    expire = datetime.utcnow() + timedelta(days=expires_days)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "license_key": license_key,
        "type": "socket_auth",  # Distinguish from web auth tokens
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_socket_token(token: str) -> Optional[dict]:
    """
    Decode and verify a socket authentication token.
    
    Args:
        token: The JWT token from socket auth
    
    Returns:
        Decoded payload with tenant_id, user_id, license_key if valid
        None if invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify it's a socket auth token
        if payload.get("type") != "socket_auth":
            return None
        
        return payload
    except JWTError:
        return None

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print(f"[DEBUG TOKEN] raw token: {token}")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        tenant_id_from_token = payload.get("tenant_id")
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
             raise HTTPException(status_code=401, detail="Token expired")
             
        if username is None:
            raise credentials_exception
    except JWTError:
        print("[DEBUG TOKEN] JWTError while decoding token")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == username).first()
    if user is None:
        if tenant_id_from_token:
            return User(id=username, tenant_id=tenant_id_from_token, username=username, is_active=True, role="viewer")
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
    """
    path = request.url.path if request else "unknown"
    auth_header = request.headers.get("Authorization") if request else "N/A"
    tenant_id = current_user.tenant_id if current_user else "N/A"
    print(f"[DEBUG AUTH] Path: {path}, Auth present: {bool(auth_header)}, sub: {current_user.username if current_user else 'N/A'}, tenant_id: {tenant_id}")

    if not current_user.tenant_id:
        # Fallback for legacy users (should not happen with new constraints)
        return "default"
    return current_user.tenant_id


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
            f"{supabase_http_service.url}/rest/v1/tenant_config?tenant_id=eq.{tenant_id}&select=subscription_status,trial_ends_at&limit=1",
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

                if trial_ends_str:
                    try:
                        trial_ends_dt = datetime.fromisoformat(trial_ends_str.replace('Z', '+00:00'))
                        if datetime.now(timezone.utc) > trial_ends_dt:
                            raise HTTPException(status_code=403, detail="Subscription expired")
                    except ValueError:
                        pass
    except httpx.RequestError as e:
        print(f"Subscription check network error: {e}")

    return tenant_id
