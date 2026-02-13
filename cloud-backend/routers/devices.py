
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import uuid
import hashlib
import random
from typing import Optional
from pydantic import BaseModel
import os
from jose import jwt

# Fix imports for Cloud Backend environment
from database import get_supabase_client

# Define local JWT utils since backend.auth is not available
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret-key") # Fallback for dev
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Mocks for compatibility with legacy register_device signature
# These allows the file to load even if backend.* modules are missing
def get_db():
    yield None

class DeviceLicense:
    pass

def get_api_key():
    pass

router = APIRouter()


def generate_license_key():
    """Generates a K24-XXXX-XXXX format license key"""
    part1 = hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()
    part2 = hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()
    return f"K24-{part1}-{part2}"

@router.post("/register")
async def register_device(
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Register device after web authentication.
    Returns a SIGNED socket_token (JWT) for secure Socket.IO auth.
    """
    from backend.auth import create_socket_token
    from backend.database import User
    
    device_id = payload.get("device_id")
    user_id = payload.get("user_id")
    app_version = payload.get("app_version")
    
    if not device_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing device_id or user_id")

    # Get user's tenant_id (critical for multi-tenancy)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Try by google_api_key (which stores Supabase UUID)
        user = db.query(User).filter(User.google_api_key == user_id).first()
    
    tenant_id = getattr(user, 'tenant_id', None) if user else None
    if not tenant_id:
        # Generate from user_id as fallback
        tenant_id = f"TENANT-{str(user_id).replace('-', '')[:8].upper()}"

    # Check if a license already exists for this device/user combo
    existing_device = db.query(DeviceLicense).filter(
        DeviceLicense.device_fingerprint == device_id,
        DeviceLicense.user_id == user_id
    ).first()

    if existing_device:
        # Reactivate or return existing
        existing_device.status = "active"
        existing_device.app_version = app_version
        existing_device.last_validated_at = datetime.now()
        db.commit()
        
        # Generate signed socket token (Phase 2 security)
        socket_token = create_socket_token(
            user_id=user_id,
            tenant_id=tenant_id,
            license_key=existing_device.license_key
        )
        
        return {
            "license_key": existing_device.license_key,
            "socket_token": socket_token,  # <-- Signed JWT for socket auth!
            "tenant_id": tenant_id
        }

    # Generate unique license key
    license_key = generate_license_key()
    
    # Create device license
    device = DeviceLicense(
        license_key=license_key,
        user_id=user_id,
        device_fingerprint=device_id,
        app_version=app_version,
        status="active",
        first_activated_at=datetime.now(),
        last_validated_at=datetime.now(),
        last_heartbeat=datetime.now()
    )
    
    try:
        db.add(device)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # Generate signed socket token (Phase 2 security)
    socket_token = create_socket_token(
        user_id=user_id,
        tenant_id=tenant_id,
        license_key=license_key
    )
    
    return {
        "license_key": license_key,
        "socket_token": socket_token,  # <-- Signed JWT for socket auth!
        "tenant_id": tenant_id
    }

class DeviceActivation(BaseModel):
    license_key: str
    tenant_id: str
    device_id: str
    device_name: Optional[str] = None

@router.post("/activate")
async def activate_device(payload: DeviceActivation):
    """
    Activate device with license key (Desktop calls this).
    Validates license, tenant, and subscription via Supabase.
    Generates JWT tokens for desktop session.
    """
    try:
        supabase = get_supabase_client()

        # 1. Validate license_key and tenant_id
        # Query tenants table to verify license ownership
        license_res = supabase.table("tenants").select("id, license_key").eq("license_key", payload.license_key).execute()
        
        if not license_res.data:
            raise HTTPException(status_code=401, detail="Invalid license key or not found")
            
        tenant_record = license_res.data[0]
        
        # Authenticate tenant ownership
        if tenant_record.get("id") != payload.tenant_id:
            raise HTTPException(status_code=403, detail="License key does not belong to this tenant")
            
        # 2. Check subscription status
        sub_res = supabase.table("subscriptions").select("*").eq("tenant_id", payload.tenant_id).order("created_at", desc=True).limit(1).execute()
        
        subscription_data = {
            "plan": "free",
            "expires_at": None
        }
        
        user_id = None
        
        if sub_res.data:
            sub = sub_res.data[0]
            # Status validation
            if sub.get("status") not in ["active", "trial"]:
                raise HTTPException(status_code=402, detail="Subscription expired or inactive")
                
            subscription_data = {
                "plan": sub.get("plan"),
                "expires_at": sub.get("expires_at")
            }
            user_id = sub.get("user_id")
        else:
            # Strict checking: if no subscription found, assume inactive/unauthorized
            raise HTTPException(status_code=402, detail="No active subscription found")

        # 3. Insert/Update device_licenses
        # Handle duplicate device_id gracefully (return existing)
        
        # Check if device already registered
        existing_dev = supabase.table("device_licenses").select("*")\
            .eq("device_fingerprint", payload.device_id)\
            .eq("tenant_id", payload.tenant_id)\
            .execute()
            
        if existing_dev.data:
            # Already exists, ensure it's active
            # We can update 'last_validated_at' here if needed
            # For now, just proceed to return existing
            pass
        else:
            # Insert new device license
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Determine user_id to fallback on if missing from subscription
            final_user_id = user_id if user_id else f"system-{payload.tenant_id}"
            
            insert_payload = {
                "device_fingerprint": payload.device_id,
                "tenant_id": payload.tenant_id,
                "license_key": payload.license_key, # Storing the Tenant License Key used for activation
                "status": "active",
                "activated_at": current_time,
                "last_validated_at": current_time,
                "user_id": final_user_id,
                "device_name": payload.device_name
            }
            
            try:
                supabase.table("device_licenses").insert(insert_payload).execute()
            except Exception as e:
                # Handle potential race conditions or constraints
                # If insert fails, log but maybe proceeds if it was a race
                print(f"Device insert warning: {e}")
                pass
                
        # 4. Generate JWT Tokens
        # Use user_id from subscription or fallback
        token_user_id = user_id if user_id else f"device-{payload.device_id}"
        
        access_claims = {
            "sub": str(token_user_id),
            "user_id": str(token_user_id),
            "tenant_id": payload.tenant_id,
            "device_id": payload.device_id
        }
        
        refresh_claims = access_claims.copy()
        refresh_claims["type"] = "refresh"
        
        access_token = create_access_token(
            data=access_claims,
            expires_delta=timedelta(days=1) # 24 hours
        )
        
        refresh_token = create_access_token(
            data=refresh_claims,
            expires_delta=timedelta(days=30) # 30 days
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "device_id": payload.device_id,
            "tenant_id": payload.tenant_id,
            "subscription": subscription_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Activation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/validate")
async def validate_device(
    license_key: str,
    device_id: str,
    db: Session = Depends(get_db)
):
    """Periodic validation (called every 5 minutes)"""
    device = db.query(DeviceLicense).filter(
        DeviceLicense.license_key == license_key,
        DeviceLicense.device_fingerprint == device_id,
        DeviceLicense.status == "active"
    ).first()
    
    if not device:
        return {"valid": False, "reason": "license_revoked_or_invalid"}
    
    # Update heartbeat
    device.last_heartbeat = datetime.now()
    db.commit()
    
    # Check if we should enforce expiry (optional future step)
    # subscription = check_subscription_status(device.user_id)
    # if not subscription["can_access"]:
    #     return {"valid": False, "reason": "subscription_expired"}
    
    return {"valid": True}
