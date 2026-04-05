import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from database import User, Company, get_db
from auth import (
    create_access_token,
    get_current_active_user
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    role: str = "owner"
    language: str = "en"


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: str
    full_name: str | None
    role: str | None
    tenant_id: str | None
    whatsapp_number: str | None = None
    language: str | None = None
    is_active: bool | None = True

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# REGISTER
# ---------------------------------------------------------------------------

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user using Supabase Auth as the master identity provider.
    After Supabase creates the auth user, we upsert only profile fields
    into the `user_profiles` ORM model (no password, no username stored).
    """
    from services.supabase_service import supabase_service, supabase_http_service

    # ------------------------------------------------------------------
    # 1. Create the auth user in Supabase
    # ------------------------------------------------------------------
    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud registration unavailable: Supabase not configured")

    try:
        auth_response = supabase_http_service.sign_up(
            email=user_data.email,
            password=user_data.password,
            user_metadata={
                "full_name": user_data.full_name,
                "company_name": user_data.company_name,
            }
        )
    except Exception as e:
        logger.error(f"Supabase sign_up failed: {e}")
        raise HTTPException(status_code=400, detail=f"Cloud registration failed: {str(e)}")

    if not (auth_response and auth_response.get("user")):
        raise HTTPException(status_code=400, detail="Supabase did not return a user after registration")

    supabase_user_id: str = auth_response["user"]["id"]

    # ------------------------------------------------------------------
    # 2. Resolve tenant_id (from profile trigger or generate locally)
    # ------------------------------------------------------------------
    tenant_id: str | None = None
    try:
        profile = supabase_service.create_user_profile(
            user_id=supabase_user_id,
            email=user_data.email,
            full_name=user_data.full_name,
        )
        if profile and profile.get("tenant_id"):
            tenant_id = profile["tenant_id"]
    except Exception as e:
        logger.warning(f"Supabase profile creation warning: {e}")

    if not tenant_id:
        # Fetch explicitly in case a DB trigger created it
        try:
            p_data = supabase_service.get_user_profile(supabase_user_id)
            if p_data and p_data.get("tenant_id"):
                tenant_id = p_data["tenant_id"]
        except Exception:
            pass

    if not tenant_id:
        tenant_id = f"K24-{supabase_user_id[:8].upper()}"
        logger.info(f"Generated local tenant_id: {tenant_id}")
        try:
            supabase_http_service.update_user_profile(supabase_user_id, {"tenant_id": tenant_id})
        except Exception as sync_err:
            logger.warning(f"Could not sync tenant_id to Supabase: {sync_err}")

    # ------------------------------------------------------------------
    # 3. Upsert profile into user_profiles via ORM
    # ------------------------------------------------------------------
    user = db.query(User).filter(User.id == supabase_user_id).first()
    if not user:
        user = User(
            id=supabase_user_id,
            tenant_id=tenant_id,
            full_name=user_data.full_name,
            company_name=user_data.company_name,
            role=user_data.role,
            language=user_data.language,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
    else:
        # profile already exists (e.g. DB trigger beat us) – patch missing fields
        user.tenant_id    = user.tenant_id    or tenant_id
        user.full_name    = user.full_name    or user_data.full_name
        user.company_name = user.company_name or user_data.company_name
        user.role         = user.role         or user_data.role
        user.language     = user.language     or user_data.language
        user.updated_at   = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # ------------------------------------------------------------------
    # 4. Create free subscription stub in Supabase
    # ------------------------------------------------------------------
    try:
        supabase_http_service.create_subscription(supabase_user_id, tenant_id, "free")
    except Exception as e:
        logger.warning(f"Supabase subscription creation warning: {e}")

    # ------------------------------------------------------------------
    # 5. Issue a local JWT (tenant_id embedded for API filtering)
    # ------------------------------------------------------------------
    access_token = create_access_token(data={
        "sub": str(supabase_user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "language": user.language,
        }
    }


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate via Supabase Auth, then load profile from user_profiles ORM.
    No local password hashes are involved.
    """
    from services.supabase_service import supabase_service, supabase_http_service

    # ------------------------------------------------------------------
    # 1. Authenticate with Supabase (mandatory for cloud backend)
    # ------------------------------------------------------------------
    if not (supabase_http_service and supabase_http_service.client):
        raise HTTPException(status_code=503, detail="Cloud auth unavailable")

    try:
        auth_response = supabase_http_service.sign_in(
            email=login_data.email,
            password=login_data.password,
        )
    except Exception as e:
        logger.warning(f"Supabase sign_in error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not (auth_response and auth_response.get("user")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_user_id: str = auth_response["user"]["id"]
    logger.info(f"Supabase login success: {login_data.email}")

    # ------------------------------------------------------------------
    # 2. Load profile from user_profiles (ORM)
    # ------------------------------------------------------------------
    user = db.query(User).filter(User.id == supabase_user_id).first()

    if not user:
        # First login on this deployment – sync profile from Supabase
        logger.info(f"First login on this deployment for {login_data.email} – syncing profile")
        try:
            profile_data = supabase_service.get_user_profile(supabase_user_id)
        except Exception:
            profile_data = None

        tenant_id = (profile_data or {}).get("tenant_id") or f"K24-{supabase_user_id[:8].upper()}"
        full_name  = (profile_data or {}).get("full_name") or "User"

        user = User(
            id=supabase_user_id,
            tenant_id=tenant_id,
            full_name=full_name,
            role=(profile_data or {}).get("role", "owner"),
            language=(profile_data or {}).get("language", "en"),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Sync tenant_id if it went stale
        if not user.tenant_id:
            try:
                p = supabase_service.get_user_profile(supabase_user_id)
                if p and p.get("tenant_id"):
                    user.tenant_id = p["tenant_id"]
            except Exception:
                pass

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled. Contact support.")

    # ------------------------------------------------------------------
    # 3. Update last_login_at
    # ------------------------------------------------------------------
    user.last_login_at = datetime.utcnow()
    db.commit()

    # ------------------------------------------------------------------
    # 4. Issue local JWT
    # ------------------------------------------------------------------
    access_token = create_access_token(data={
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "email_verification_pending": not getattr(user, 'is_verified', True)
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "language": user.language,
            "email_verification_pending": not getattr(user, 'is_verified', True)
        }
    }


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "role": current_user.role,
        "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
        "whatsapp_number": current_user.whatsapp_number if hasattr(current_user, "whatsapp_number") else None,
        "language": current_user.language if hasattr(current_user, "language") else None,
        "is_active": current_user.is_active,
    }


# ---------------------------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------------------------

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# CHANGE PASSWORD (delegates entirely to Supabase)
# ---------------------------------------------------------------------------

class PasswordChangeRequest(BaseModel):
    new_password: str   # Old password is validated by Supabase re-auth if needed


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
):
    from services.supabase_service import supabase_service
    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")
    try:
        supabase_service.client.auth.update_user({"password": request.new_password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Password change failed: {str(e)}")
    return {"message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# FORGOT PASSWORD
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Send password reset email via Supabase."""
    from services.supabase_service import supabase_service

    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")

    try:
        supabase_service.client.auth.reset_password_for_email(
            request.email,
            options={"redirect_to": "https://your-app.vercel.app/reset-password"}
        )
    except Exception as e:
        logger.warning(f"Password reset error for {request.email}: {e}")

    return {
        "message": "If an account exists with this email, a password reset link has been sent.",
        "success": True
    }


# ---------------------------------------------------------------------------
# RESET PASSWORD
# ---------------------------------------------------------------------------

class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password using token from Supabase email link."""
    from services.supabase_service import supabase_service

    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")

    try:
        supabase_service.client.auth.set_session(request.access_token, "")
        response = supabase_service.client.auth.update_user({"password": request.new_password})
        if response.user:
            return {"message": "Password reset successfully", "success": True}
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")


# ---------------------------------------------------------------------------
# SUBSCRIPTION STATUS
# ---------------------------------------------------------------------------

@router.get("/subscription")
async def get_subscription_status(current_user: User = Depends(get_current_active_user)):
    """Get current user's subscription status from Supabase."""
    from services.supabase_service import supabase_service

    if not supabase_service.client:
        return {
            "status": "offline",
            "plan": "free",
            "can_access": True,
            "message": "Working in offline mode"
        }

    try:
        result = supabase_service.client.rpc(
            "check_subscription_status",
            {"p_user_id": current_user.id}
        ).execute()

        if result.data:
            return result.data
        return {"status": "no_subscription", "plan": "free", "can_access": True, "trial_ends_at": None}
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return {"status": "error", "plan": "free", "can_access": True, "message": "Unable to verify subscription"}


# ---------------------------------------------------------------------------
# VERIFY EMAIL
# ---------------------------------------------------------------------------

@router.get("/verify-email")
async def verify_email_callback(token: str, type: str):
    """Handle email verification callback from Supabase."""
    from services.supabase_service import supabase_service

    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")

    try:
        if type in ("signup", "email"):
            response = supabase_service.client.auth.verify_otp({"token_hash": token, "type": type})
            if response.user:
                return {"message": "Email verified successfully", "success": True, "redirect": "/login"}
        raise HTTPException(status_code=400, detail="Invalid verification link")
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")


# ---------------------------------------------------------------------------
# RESEND VERIFICATION
# ---------------------------------------------------------------------------

class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/resend-verification")
async def resend_verification_email(request: ResendVerificationRequest):
    """Resend email verification link."""
    from services.supabase_service import supabase_service

    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")

    try:
        supabase_service.client.auth.resend(
            type="signup",
            email=request.email,
            options={"redirect_to": "https://your-app.vercel.app/auth/callback"}
        )
    except Exception as e:
        logger.warning(f"Resend verification error: {e}")

    return {
        "message": "If an unverified account exists, a verification email has been sent.",
        "success": True
    }
