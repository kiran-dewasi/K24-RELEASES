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
    """
    Activate device with license key (Desktop calls this).
    
    Process:
    1. Get local device_id from device service
    2. Call cloud /api/devices/activate endpoint (using auth_client)
    3. Store returned tokens via token storage service
    4. Return success payload to frontend
    
    Note: This endpoint is for INITIAL activation and does NOT use
    the token refresh middleware (since there are no tokens yet).
    Subsequent cloud calls should use get_cloud_client() for auto-refresh.
    """
    import logging
    import socket
    from desktop.services.device_service import get_device_id
    from desktop.services.token_storage import save_tokens
    from backend.services.config_service import get_cloud_url
    
    # Use standard requests for activation (no tokens yet)
    import requests
    
    logger = logging.getLogger(__name__)
    
    license_key = payload.get("license_key")
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")  # May be passed from deep link
    
    if not license_key:
        raise HTTPException(status_code=400, detail="Missing license_key")
    
    try:
        # Get local device ID
        device_id = get_device_id()
        
        # Determine cloud URL (from config service)
        cloud_url = get_cloud_url()
        activation_url = f"{cloud_url}/api/devices/activate"
        
        # Prepare activation payload
        activation_payload = {
            "license_key": license_key,
            "device_id": device_id
        }
        
        # Add optional fields if provided
        if tenant_id:
            activation_payload["tenant_id"] = tenant_id
        if not activation_payload.get("device_name"):
            activation_payload["device_name"] = socket.gethostname()
        
        # Call cloud activation endpoint
        # Note: We use requests directly here since we don't have tokens yet
        logger.info(f"Activating device with cloud at {activation_url}")
        response = requests.post(
            activation_url,
            json=activation_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            error_detail = response.json().get("detail", "Activation failed") if response.headers.get("content-type", "").startswith("application/json") else response.text
            logger.error(f"Cloud activation failed: {response.status_code} - {error_detail}")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )
        
        # Parse successful response
        activation_data = response.json()
        access_token = activation_data.get("access_token")
        refresh_token = activation_data.get("refresh_token")
        activated_tenant_id = activation_data.get("tenant_id")
        subscription = activation_data.get("subscription", {})
        
        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=500,
                detail="Cloud activation did not return tokens"
            )
        
        # Store tokens securely
        logger.info(f"Storing activation tokens for tenant: {activated_tenant_id}")
        save_tokens(access_token, refresh_token, tenant_id=activated_tenant_id)
        
        # Return concise success payload to frontend
        return {
            "success": True,
            "tenant_id": activated_tenant_id,
            "device_id": device_id,
            "subscription": subscription,
            "user_id": activation_data.get("user_id"),
            "message": "Device activated successfully"
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during activation: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach cloud activation service: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during activation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Activation error: {str(e)}"
        )

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


@router.get("/status")
async def get_device_status():
    """
    Example endpoint demonstrating CloudAPIClient with auto token refresh.
    
    Makes an authenticated call to the cloud backend to get device/subscription status.
    If the access token is expired, the client will automatically:
    1. Call the refresh endpoint
    2. Update stored tokens
    3. Retry the original request
    
    Returns:
        Device and subscription status from cloud
    """
    import logging
    from backend.middleware.auth_client import get_cloud_client
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get authenticated cloud client
        client = get_cloud_client()
        
        # Make authenticated call - token refresh happens automatically
        logger.info("Fetching device status from cloud")
        response = client.get("/api/devices/me")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            # This means token refresh also failed
            raise HTTPException(
                status_code=401,
                detail="Authentication failed - please re-activate device"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Cloud API error: {response.text}"
            )
            
    except Exception as e:
        logger.error(f"Failed to get device status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )
