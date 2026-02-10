from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import hashlib
import random

from backend.database import get_db, DeviceLicense
from backend.dependencies import get_api_key

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

@router.post("/activate")
async def activate_device(
    payload: dict,
    db: Session = Depends(get_db)
):
    """Activate device with license key (Desktop calls this)"""
    license_key = payload.get("license_key")
    device_id = payload.get("device_id")

    device = db.query(DeviceLicense).filter(
        DeviceLicense.license_key == license_key,
        DeviceLicense.device_fingerprint == device_id
    ).first()
    
    if not device:
        raise HTTPException(status_code=401, detail="Invalid license")
    
    # Update heartbeat
    device.last_heartbeat = datetime.now()
    device.status = "active"
    db.commit()
    
    return {
        "status": "valid",
        "user_id": device.user_id
    }

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
