from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, Tenant, TenantConfig
from auth import get_current_active_user, User

router = APIRouter(prefix="/api", tags=["tenant-config"])

class TenantWhatsappConfigRequest(BaseModel):
    whatsapp_number: str | None = None
    is_active: bool = True

@router.get("/tenant/whatsapp-config")
async def get_tenant_whatsapp_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    cfg = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    return {
        "tenant_id": tenant_id,
        "whatsapp_number": cfg.whatsapp_number if cfg else None,
        "is_active": cfg.is_whatsapp_active if cfg else True,
    }

@router.put("/tenant/whatsapp-config")
async def update_tenant_whatsapp_config(
    body: TenantWhatsappConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # 1. Authorize: only owner/admin.
    print(f"[DEBUG ROLE] current_user.role = '{current_user.role}'")
    if str(current_user.role).lower() not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant_id on current user")

    # 2. Update local SQLite Tenant (if whatsapp_number field exists)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant:
        tenant.whatsapp_number = body.whatsapp_number
        db.add(tenant)

    # 3. Update or upsert TenantConfig row
    cfg = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not cfg:
        cfg = TenantConfig(tenant_id=tenant_id)
        db.add(cfg)

    cfg.whatsapp_number = body.whatsapp_number
    cfg.is_whatsapp_active = body.is_active

    db.commit()
    db.refresh(cfg)

    # 4. Sync to Supabase tenant_config via HTTP PATCH/UPSERT
    try:
        from services.supabase_service import supabase_http_service
        if supabase_http_service.client:
            import httpx
            headers = supabase_http_service._get_headers(use_service_key=True)

            payload = {
                "tenant_id": tenant_id,
                "whatsapp_number": body.whatsapp_number,
                "is_whatsapp_active": body.is_active,
            }

            # Use upsert semantics via POST with on_conflict if your setup supports it,
            # or PATCH if row is guaranteed to exist.
            httpx.post(
                f"{supabase_http_service.url}/rest/v1/tenant_config?on_conflict=tenant_id",
                headers=headers,
                json=payload,
                timeout=10,
            )
    except Exception as e:
        print(f"⚠️ Supabase tenant_config sync warning (non-fatal): {e}")

    return {
        "tenant_id": tenant_id,
        "whatsapp_number": cfg.whatsapp_number,
        "is_active": cfg.is_whatsapp_active,
    }
