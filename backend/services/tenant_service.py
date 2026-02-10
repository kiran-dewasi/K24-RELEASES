"""
Tenant Service - Central Hub for Multi-Tenant Operations
=========================================================
This service ensures tenant data is consistent across Supabase (Cloud) and SQLite (Local).

Key Responsibilities:
1. Generate tenant_id from user UUID
2. Create/sync tenants in both databases
3. Ensure tenant exists locally before any operation
"""

import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class TenantService:
    """
    Central service for tenant management.
    Ensures tenant exists in BOTH Supabase and SQLite.
    """
    
    @staticmethod
    def generate_tenant_id(user_id: str) -> str:
        """
        Generate a tenant_id from a Supabase user UUID.
        Format: TENANT-{first 8 chars uppercase}
        
        Example: 
            user_id = "84f03f7d-1234-5678-abcd-efgh12345678"
            returns = "TENANT-84F03F7D"
        """
        if not user_id:
            return "TENANT-UNKNOWN"
        
        # Remove hyphens and take first 8 chars
        clean_id = user_id.replace("-", "")[:8].upper()
        return f"TENANT-{clean_id}"
    
    def create_tenant_cloud(self, tenant_id: str, company_name: str, 
                           tally_company_name: str = None,
                           whatsapp_number: str = None) -> Optional[Dict]:
        """
        Create tenant record in Supabase (Cloud).
        Uses the HTTP-based service to avoid library issues.
        """
        from backend.services.supabase_service import supabase_http_service
        
        if not supabase_http_service.client:
            logger.warning("Supabase not available, skipping cloud tenant creation")
            return None
        
        try:
            import httpx
            response = httpx.post(
                f"{supabase_http_service.url}/rest/v1/tenants",
                headers=supabase_http_service._get_headers(use_service_key=True),
                json={
                    "id": tenant_id,
                    "company_name": company_name,
                    "tally_company_name": tally_company_name,
                    "whatsapp_number": whatsapp_number
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"[CLOUD] Created tenant: {tenant_id}")
                return data[0] if isinstance(data, list) and data else data
            elif response.status_code == 409:
                # Already exists - not an error
                logger.info(f"[CLOUD] Tenant already exists: {tenant_id}")
                return {"id": tenant_id, "exists": True}
            else:
                logger.warning(f"[CLOUD] Tenant creation returned {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"[CLOUD] Tenant creation failed: {e}")
            return None
    
    def create_tenant_local(self, db_session, tenant_id: str, company_name: str,
                           tally_company_name: str = None,
                           whatsapp_number: str = None) -> Optional[object]:
        """
        Create tenant record in SQLite (Local).
        Safe: Won't fail if tenant already exists.
        """
        from backend.database import Tenant
        
        try:
            # Check if exists
            existing = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
            if existing:
                logger.info(f"[LOCAL] Tenant already exists: {tenant_id}")
                return existing
            
            # Create new
            tenant = Tenant(
                id=tenant_id,
                company_name=company_name,
                tally_company_name=tally_company_name,
                whatsapp_number=whatsapp_number,
                created_at=datetime.now()
            )
            db_session.add(tenant)
            db_session.commit()
            db_session.refresh(tenant)
            
            logger.info(f"[LOCAL] Created tenant: {tenant_id}")
            return tenant
            
        except Exception as e:
            logger.error(f"[LOCAL] Tenant creation failed: {e}")
            db_session.rollback()
            return None
    
    def create_tenant_both(self, db_session, user_id: str, company_name: str,
                          tally_company_name: str = None) -> str:
        """
        Create tenant in BOTH Supabase and SQLite.
        This is the primary method to call during registration.
        
        Returns: tenant_id
        """
        tenant_id = self.generate_tenant_id(user_id)
        
        # 1. Create in cloud (non-blocking)
        self.create_tenant_cloud(tenant_id, company_name, tally_company_name)
        
        # 2. Create in local (critical)
        self.create_tenant_local(db_session, tenant_id, company_name, tally_company_name)
        
        logger.info(f"[SYNC] Tenant created in both databases: {tenant_id}")
        return tenant_id
    
    def ensure_tenant_local(self, db_session, tenant_id: str) -> Optional[object]:
        """
        Ensure tenant exists locally. If not, try to fetch from cloud.
        Call this during login to sync missing tenants.
        """
        from backend.database import Tenant
        from backend.services.supabase_service import supabase_http_service
        
        # Check local first
        tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            return tenant
        
        # Missing locally - try to fetch from cloud
        logger.info(f"[SYNC] Tenant missing locally, fetching from cloud: {tenant_id}")
        
        if supabase_http_service.client:
            try:
                import httpx
                response = httpx.get(
                    f"{supabase_http_service.url}/rest/v1/tenants?id=eq.{tenant_id}",
                    headers=supabase_http_service._get_headers(use_service_key=True),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        cloud_tenant = data[0]
                        return self.create_tenant_local(
                            db_session,
                            tenant_id,
                            cloud_tenant.get('company_name', 'Unknown'),
                            cloud_tenant.get('tally_company_name'),
                            cloud_tenant.get('whatsapp_number')
                        )
            except Exception as e:
                logger.error(f"[SYNC] Failed to fetch tenant from cloud: {e}")
        
        # Create a placeholder if nothing found
        logger.warning(f"[SYNC] Creating placeholder tenant locally: {tenant_id}")
        return self.create_tenant_local(db_session, tenant_id, "Unknown Company")
    
    def get_tenant(self, db_session, tenant_id: str) -> Optional[object]:
        """Get tenant from local database"""
        from backend.database import Tenant
        return db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    def update_tenant(self, db_session, tenant_id: str, **kwargs) -> Optional[object]:
        """
        Update tenant in local database.
        Accepts: company_name, tally_company_name, whatsapp_number, auto_post_to_tally
        """
        from backend.database import Tenant
        
        tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return None
        
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        db_session.commit()
        db_session.refresh(tenant)
        
        # Also update cloud (best effort)
        self._sync_tenant_to_cloud(tenant_id, kwargs)
        
        return tenant
    
    def _sync_tenant_to_cloud(self, tenant_id: str, data: Dict):
        """Sync tenant updates to Supabase (best effort)"""
        from backend.services.supabase_service import supabase_http_service
        
        if not supabase_http_service.client:
            return
        
        try:
            import httpx
            response = httpx.patch(
                f"{supabase_http_service.url}/rest/v1/tenants?id=eq.{tenant_id}",
                headers=supabase_http_service._get_headers(use_service_key=True),
                json=data,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"[CLOUD] Tenant synced: {tenant_id}")
            else:
                logger.warning(f"[CLOUD] Tenant sync failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"[CLOUD] Tenant sync error: {e}")


# Global instance
tenant_service = TenantService()
