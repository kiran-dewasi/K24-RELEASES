from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from database import User, Company, UserSettings, get_db
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    company_name: str
    role: str = "viewer"  # Default role; fixed up during creation

class CompanySetup(BaseModel):
    gstin: str | None = None
    pan: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    phone: str | None = None
    tally_company_name: str
    tally_url: str = "http://localhost:9000"
    tally_edu_mode: bool = False
    google_api_key: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    company_id: int | None
    tenant_id: str | None
    whatsapp_number: str | None
    is_whatsapp_verified: bool | None = False
    subscription_status: str | None = None
    trial_ends_at: str | None = None

    class Config:
        from_attributes = True

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register new user in Supabase + create local session (Hybrid approach)
    """
    from services.supabase_service import supabase_service, supabase_http_service
    from services.tenant_service import tenant_service
    import uuid

    # 1. Supabase Registration (Cloud Master)
    # ---------------------------------------------
    user_id = None
    tenant_id = None
    
    # Check if we can talk to Supabase
    if supabase_service.client:
        try:
            # A. Create Auth User (using HTTP service)
            auth_response = supabase_http_service.sign_up(
                email=user_data.email,
                password=user_data.password,
                user_metadata={
                    "full_name": user_data.full_name,
                    "company_name": user_data.company_name
                }
            )
            
            # Check for user in response
            if auth_response and auth_response.get('user'):
                user_id = auth_response['user']['id']
                
                # B. Create Profile (User) - Trigger will handle tenant_id creation usually
                try:
                    profile = supabase_service.create_user_profile(
                        user_id=user_id,
                        email=user_data.email,
                        full_name=user_data.full_name
                    )
                    
                    # Fetch the generated tenant_id if not returned immediately
                    if profile and 'tenant_id' in profile and profile['tenant_id']:
                         tenant_id = profile['tenant_id']
                    else:
                         # Fetch explicitly
                         p_data = supabase_service.get_user_profile(user_id)
                         if p_data and p_data.get('tenant_id'):
                             tenant_id = p_data.get('tenant_id')

                except Exception as e:
                    print(f"Supabase Profile Creation Warning: {e}")

                # C. If still no tenant_id, generate one locally and sync back to Supabase
                if not tenant_id and user_id:
                    tenant_id = f"TENANT-{user_id[:8].upper()}"
                    print(f"Generated local tenant_id: {tenant_id}")
                    
                    # SYNC BACK: Update Supabase profile with generated tenant_id
                    try:
                        supabase_http_service.update_user_profile(user_id, {"tenant_id": tenant_id})
                        print(f"✅ Synced tenant_id to Supabase: {tenant_id}")
                    except Exception as sync_err:
                        print(f"⚠️ Could not sync tenant_id to Supabase: {sync_err}")

                # D. Create Subscription (using HTTP service)
                if tenant_id and user_id:
                    try:
                        supabase_http_service.create_subscription(user_id, tenant_id, "free")
                    except Exception as e:
                         print(f"Supabase Subscription Warning: {e}")
                
                # E. Create Trial configuration in tenant_config
                if tenant_id and user_id:
                    try:
                        # For desktop signups, we don't have whatsapp number yet, so we pass None
                        supabase_http_service.create_tenant_config(
                            tenant_id=tenant_id,
                            email=user_data.email, 
                            company_name=user_data.company_name,
                            whatsapp_number=None
                        )
                    except Exception as e:
                         print(f"Supabase Trial Setup Warning: {e}")

        except Exception as e:
            # If Supabase fails (e.g. offline), should we fail strictly or allow local-only?
            # Prompt implies Supabase is Master. We should probably fail or warn.
            # For robustness, we will FAIL if cloud is required.
            print(f"Supabase Registration Failed: {e}")
            raise HTTPException(status_code=400, detail=f"Cloud registration failed: {str(e)}")
    else:
        # Supabase not configured - generate local tenant_id
        tenant_id = f"TENANT-{uuid.uuid4().hex[:8].upper()}"
        print(f"Offline mode - Generated local tenant_id: {tenant_id}")

    # 2. Local Registration (Business Data Replica)
    # ---------------------------------------------
    
    # Check if user exists locally
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered locally")
    
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken locally")
    
    # Phase 1: Ensure tenant exists locally (synced with cloud)
    # This creates the tenant in SQLite if not already present
    if tenant_id:
        tenant_service.create_tenant_local(
            db, tenant_id, user_data.company_name,
            tally_company_name=None  # Will be set during Tally setup
        )
    
    # Create company locally
    company = Company(
        name=user_data.company_name,
        created_at=datetime.now(),
        # TODO: demo/test fallback. NOT used for authenticated flows.
        tenant_id=tenant_id or "offline-default" # Sync tenant_id
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    
    # Create user locally
    hashed_password = get_password_hash(user_data.password)
    is_first_user = db.query(User).first() is None
    assigned_role = 'owner' if is_first_user else 'viewer'
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=assigned_role,
        company_id=company.id,
        # TODO: demo/test fallback. NOT used for authenticated flows.
        tenant_id=tenant_id or "offline-default", # Sync tenant_id
        is_verified=True,  # Auto-verify first user
        created_at=datetime.now(),
        google_api_key=user_id # Store Supabase UUID in google_api_key for now as a reference or add a new column later
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create default settings
    # TODO: demo/test fallback. NOT used for authenticated flows.
    settings = UserSettings(user_id=user.id, tenant_id=tenant_id or "offline-default")
    db.add(settings)
    db.commit()
    
    # Create access token (Local Session)
    # Include tenant_id in JWT for API filtering (Phase 1 security)
    access_token = create_access_token(data={
        "sub": user.username,
        "tenant_id": tenant_id  # Now embedded in token!
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "company_id": user.company_id,
            "tenant_id": tenant_id
        }
    }

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Hybrid Login:
    1. Authenticate with Supabase (Cloud Master)
    2. Sync/Verify Local User (Business Replica)
    3. Return Local Session Token
    """
    from services.supabase_service import supabase_service, supabase_http_service
    from services.tenant_service import tenant_service
    
    # 1. Supabase Authentication (Priority)
    # -------------------------------------
    supabase_user_id = None
    supabase_auth_token = None
    
    if supabase_http_service.client:
        try:
            # Use HTTP service for login (not broken client.auth)
            auth_response = supabase_http_service.sign_in(
                email=login_data.email,
                password=login_data.password
            )
            
            if auth_response and auth_response.get('user'):
                supabase_user_id = auth_response['user']['id']
                supabase_auth_token = auth_response.get('access_token')
                print(f"✅ Supabase Login Success: {login_data.email}")
            else:
                 print(f"⚠️ Supabase Login Failed (Invalid Credentials or No Session)")
        except Exception as e:
            # If invalid credentials, Supabase raises an error
            print(f"Supabase Auth Error: {e}")
            # If it's a "Invalid login credentials" error, we might want to stop early?
            # BUT: We must support Offline Mode. If Supabase is unreachable, we default to local check.
            # If Supabase REJECTED the password (400), strictly we should fail.
            # However, detecting "wrong password" vs "offline" can be tricky with generic exceptions.
            # For now, we fall back to local check functionality if Supabase login fails/errors.
            pass

    # 2. Local Authentication / User Sync
    # -----------------------------------
    try:
        # A. Look up local user
        user = db.query(User).filter(User.email == login_data.email).first()
        
        # B. Logic Fork
        if user:
            # User exists locally.
            # If we had a successful Supabase login, we trust that.
            # If Supabase failed (offline?), we check local password hash.
            if not supabase_user_id:
                # Cloud login failed/skipped -> Check local password
                if not verify_password(login_data.password, user.hashed_password):
                     raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect email or password (Local Check)",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            else:
                # Cloud login SUCCESS. Sync tenant_id from Supabase if local is wrong/missing.
                LEGACY_TENANT_IDS = ['TENANT-12345', 'tenant-12345', '12345', 'offline-default', '']
                if user.tenant_id is None or user.tenant_id in LEGACY_TENANT_IDS:
                    # Fetch tenant_id from Supabase profile
                    profile = supabase_service.get_user_profile(supabase_user_id)
                    if profile and profile.get('tenant_id'):
                        user.tenant_id = profile['tenant_id']
                        db.commit()
                        print(f"✅ Synced tenant_id from Supabase: {user.tenant_id}")
                
        else:
            # User DOES NOT EXIST locally.
            # If Supabase login succeeded, we should auto-create the local replica (First login on this device).
            if supabase_user_id:
                print(f"🔄 Syncing Supabase User to Local DB: {login_data.email}")
                
                # Fetch profile for extra details
                profile = supabase_service.get_user_profile(supabase_user_id)
                full_name = profile.get('full_name') if profile else "Supabase User"
                tenant_id = profile.get('tenant_id') if profile else f"TENANT-{supabase_user_id[:8].upper()}"
                
                # Create Company Stub
                company = Company(
                    name=profile.get('company_name', 'My Company'),
                    created_at=datetime.now(),
                    tenant_id=tenant_id
                )
                db.add(company)
                db.commit()
                db.refresh(company)
                
                # Create User Stub
                hashed_pw = get_password_hash(login_data.password) # Campure current password locally for offline access next time
                is_first_user = db.query(User).first() is None
                assigned_role = 'owner' if is_first_user else 'viewer'
                
                user = User(
                    email=login_data.email,
                    username=login_data.email.split('@')[0], # Fallback username
                    hashed_password=hashed_pw,
                    full_name=full_name,
                    role=assigned_role,
                    company_id=company.id,
                    tenant_id=tenant_id,
                    is_verified=True,
                    is_active=True,
                    created_at=datetime.now(),
                    google_api_key=supabase_user_id
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                
                # Create Settings Stub
                settings = UserSettings(user_id=user.id, tenant_id=tenant_id)
                db.add(settings)
                db.commit()
                
                # Phase 1: Ensure tenant exists in local SQLite
                tenant_service.create_tenant_local(
                    db, tenant_id, 
                    profile.get('company_name', 'My Company'),
                    tally_company_name=profile.get('tally_company_name')
                )
                
            else:
                # Neither Cloud nor Local found the user/password valid
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        if not user.is_active:
            raise HTTPException(status_code=400, detail="User account is disabled")
        
        # Update last login
        user.last_login = datetime.now()
        db.commit()
        
        # 3. Create Session Token (Local Access)
        # Include tenant_id in JWT for API filtering (Phase 1 security)
        access_token = create_access_token(data={
            "sub": user.username,
            "tenant_id": getattr(user, 'tenant_id', None)  # Embedded for security!
        })
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "company_id": user.company_id,
                "tenant_id": getattr(user, 'tenant_id', None) # Safely get if column missing (handled by migration script)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    from services.supabase_service import supabase_service

    response_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "company_id": current_user.company_id,
        "tenant_id": current_user.tenant_id,
        "whatsapp_number": current_user.whatsapp_number,
        "is_whatsapp_verified": getattr(current_user, "is_whatsapp_verified", False) or False,
        "subscription_status": None,
        "trial_ends_at": None,
    }

    # Append trial / subscription info from Supabase (fail silently)
    from services.supabase_service import supabase_http_service
    if current_user.tenant_id and supabase_http_service.client:
        try:
            import httpx
            headers = supabase_http_service._get_headers(use_service_key=True)
            response = httpx.get(
                f"{supabase_http_service.url}/rest/v1/tenant_config?tenant_id=eq.{current_user.tenant_id}&select=subscription_status,trial_ends_at&limit=1",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    response_dict["subscription_status"] = data[0].get("subscription_status")
                    response_dict["trial_ends_at"] = data[0].get("trial_ends_at")
        except Exception as e:
            print(f"Failed to fetch trial info: {e}")
            pass  # fail silently — don't break login

    return response_dict

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    whatsapp_number: str | None = None
    mobile: str | None = None

@router.put("/profile")
async def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile (full_name, whatsapp_number, mobile). Syncs to Supabase."""
    # NEW CODE START
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if profile_data.full_name is not None:
        user.full_name = profile_data.full_name

    new_whatsapp = profile_data.whatsapp_number or profile_data.mobile
    if new_whatsapp is not None:
        user.whatsapp_number = new_whatsapp

    db.commit()
    db.refresh(user)

    # ── Sync to Supabase (non-blocking, best-effort) ──────────────────────────
    supabase_user_id = current_user.google_api_key  # Supabase UUID stored here
    tenant_id = current_user.tenant_id

    try:
        from services.supabase_service import supabase_http_service
        if supabase_http_service.client:
            import httpx
            headers = supabase_http_service._get_headers(use_service_key=True)

            # 1. Update public.user_profiles
            profile_update: dict = {}
            if profile_data.full_name is not None:
                profile_update["full_name"] = profile_data.full_name
            if new_whatsapp is not None:
                profile_update["whatsapp_number"] = new_whatsapp

            if profile_update and supabase_user_id:
                httpx.patch(
                    f"{supabase_http_service.url}/rest/v1/user_profiles?id=eq.{supabase_user_id}",
                    headers=headers,
                    json=profile_update,
                    timeout=10
                )

            # 2. Update public.tenants.whatsapp_number when phone changes
            # ---> REMOVED: tenant_config is now the single source of truth for whatsapp_number.
            # if new_whatsapp is not None and tenant_id:
            #     httpx.patch(
            #         f"{supabase_http_service.url}/rest/v1/tenants?id=eq.{tenant_id}",
            #         headers=headers,
            #         json={"whatsapp_number": new_whatsapp},
            #         timeout=10
            #     )
            #     print(f"✅ Synced whatsapp_number to Supabase tenant {tenant_id}: {new_whatsapp}")

    except Exception as e:
        print(f"⚠️ Supabase profile sync warning (non-fatal): {e}")

    return {
        "status": "success",
        "user": {
            "full_name": user.full_name,
            "whatsapp_number": user.whatsapp_number,
            "email": current_user.email,
            "role": current_user.role,
        }
    }

@router.post("/setup-company")
def setup_company(
    company_data: CompanySetup,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can setup company")
    
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update company details
    company.gstin = company_data.gstin
    company.pan = company_data.pan
    company.address = company_data.address
    company.city = company_data.city
    company.state = company_data.state
    company.pincode = company_data.pincode
    company.phone = company_data.phone
    company.tally_company_name = company_data.tally_company_name
    company.tally_url = company_data.tally_url
    company.tally_edu_mode = company_data.tally_edu_mode
    
    # Update user's Google API key
    if company_data.google_api_key:
        current_user.google_api_key = company_data.google_api_key
    
    db.commit()
    
    return {"status": "success", "message": "Company setup completed"}

@router.get("/check-setup")
def check_setup_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    
    setup_complete = bool(
        company and 
        company.tally_company_name and
        company.gstin
    )
    
    return {
        "setup_complete": setup_complete,
        "company": {
            "name": company.name if company else None,
            "gstin": company.gstin if company else None,
            "tally_configured": bool(company and company.tally_company_name)
        } if company else None
    }

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/logout")
async def logout():
    # JWT is stateless, so just return success
    # Frontend will delete token from localStorage
    # In a more complex setup, we might blacklist the token here.
    return {"message": "Logged out successfully"}

@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify old password
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password incorrect")
    
    # Update password
    new_hash = get_password_hash(request.new_password)
    current_user.hashed_password = new_hash
    db.commit()
    
    return {"message": "Password changed successfully"}


# ============================================
# NEW: FORGOT PASSWORD (Supabase Email)
# ============================================
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send password reset email via Supabase.
    Always returns success to prevent email enumeration.
    """
    from services.supabase_service import supabase_service
    
    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")
    
    try:
        # Supabase will send password reset email
        supabase_service.client.auth.reset_password_for_email(
            request.email,
            options={
                "redirect_to": "https://your-app.vercel.app/reset-password"
            }
        )
    except Exception as e:
        # Log error but don't expose it (security)
        print(f"Password reset error for {request.email}: {e}")
    
    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with this email, a password reset link has been sent.",
        "success": True
    }


# ============================================
# NEW: RESET PASSWORD (After email link)
# ============================================
class ResetPasswordRequest(BaseModel):
    access_token: str  # Token from Supabase email link
    new_password: str

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using token from Supabase email.
    Frontend extracts token from URL after user clicks email link.
    """
    from services.supabase_service import supabase_service
    
    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")
    
    try:
        # Set session with recovery token
        supabase_service.client.auth.set_session(request.access_token, "")
        
        # Update password in Supabase
        response = supabase_service.client.auth.update_user({
            "password": request.new_password
        })
        
        if response.user:
            # Also update local password hash
            user = db.query(User).filter(User.email == response.user.email).first()
            if user:
                user.hashed_password = get_password_hash(request.new_password)
                db.commit()
            
            return {"message": "Password reset successfully", "success": True}
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
            
    except Exception as e:
        print(f"Password reset error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")


# ============================================
# NEW: GET SUBSCRIPTION STATUS
# ============================================
@router.get("/subscription")
async def get_subscription_status(current_user: User = Depends(get_current_active_user)):
    """
    Get current user's subscription status from Supabase.
    """
    from services.supabase_service import supabase_service
    
    if not supabase_service.client:
        # Return default free status if cloud unavailable
        return {
            "status": "offline",
            "plan": "free",
            "can_access": True,
            "message": "Working in offline mode"
        }
    
    try:
        # Get user's Supabase ID (stored in google_api_key field)
        supabase_user_id = current_user.google_api_key
        
        if not supabase_user_id:
            return {
                "status": "local_only",
                "plan": "free",
                "can_access": True,
                "message": "Local account - no cloud subscription"
            }
        
        # Call Supabase function to check subscription
        result = supabase_service.client.rpc(
            'check_subscription_status',
            {'p_user_id': supabase_user_id}
        ).execute()
        
        if result.data:
            return result.data
        else:
            return {
                "status": "no_subscription",
                "plan": "free",
                "can_access": True,
                "trial_ends_at": None
            }
            
    except Exception as e:
        print(f"Subscription check error: {e}")
        return {
            "status": "error",
            "plan": "free",
            "can_access": True,
            "message": "Unable to verify subscription"
        }


# ============================================
# NEW: VERIFY EMAIL (Callback)
# ============================================
@router.get("/verify-email")
async def verify_email_callback(token: str, type: str, db: Session = Depends(get_db)):
    """
    Handle email verification callback from Supabase.
    Supabase redirects here after user clicks verification link.
    """
    from services.supabase_service import supabase_service
    
    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")
    
    try:
        if type == "signup" or type == "email":
            # Verify the token with Supabase
            response = supabase_service.client.auth.verify_otp({
                "token_hash": token,
                "type": type
            })
            
            if response.user:
                return {
                    "message": "Email verified successfully",
                    "success": True,
                    "redirect": "/login"
                }
        
        raise HTTPException(status_code=400, detail="Invalid verification link")
        
    except Exception as e:
        print(f"Email verification error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")


# ============================================
# NEW: RESEND VERIFICATION EMAIL
# ============================================
class ResendVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/resend-verification")
async def resend_verification_email(request: ResendVerificationRequest):
    """
    Resend email verification link.
    """
    from services.supabase_service import supabase_service
    
    if not supabase_service.client:
        raise HTTPException(status_code=503, detail="Cloud service unavailable")
    
    try:
        supabase_service.client.auth.resend(
            type="signup",
            email=request.email,
            options={
                "redirect_to": "https://your-app.vercel.app/auth/callback"
            }
        )
    except Exception as e:
        print(f"Resend verification error: {e}")
    
    # Always return success
    return {
        "message": "If an unverified account exists, a verification email has been sent.",
        "success": True
    }

