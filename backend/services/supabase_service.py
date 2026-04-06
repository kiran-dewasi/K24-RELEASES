"""
Supabase HTTP Service - Uses direct HTTP calls instead of supabase-py
This version supports the new sb_publishable_ and sb_secret_ key formats
"""
import httpx
import os
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

class SupabaseHTTPService:
    """
    Handles all Supabase operations using direct HTTP calls
    Compatible with new Supabase API key format (sb_publishable_, sb_secret_)
    """
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.anon_key:
            print("Warning: Supabase credentials missing. SupabaseHTTPService operations will fail.")
            self.client = None
        else:
            self.client = True  # Flag to indicate service is configured
            
    def _get_headers(self, use_service_key: bool = False) -> Dict[str, str]:
        """Get headers for Supabase API calls"""
        key = self.service_key if use_service_key else self.anon_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def _rest_url(self, table: str) -> str:
        """Get REST API URL for a table"""
        return f"{self.url}/rest/v1/{table}"
    
    def _auth_url(self, endpoint: str) -> str:
        """Get Auth API URL"""
        return f"{self.url}/auth/v1/{endpoint}"
    
    # ============================================
    # AUTH OPERATIONS
    # ============================================
    
    def sign_up(self, email: str, password: str, user_metadata: Optional[Dict] = None) -> Dict:
        """Register a new user via Supabase Auth"""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        payload = {
            "email": email,
            "password": password
        }
        if user_metadata:
            payload["data"] = user_metadata
        
        response = httpx.post(
            self._auth_url("signup"),
            headers=self._get_headers(),
            json=payload,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            error_data = response.json() if response.text else {"message": "Unknown error"}
            raise Exception(error_data.get("msg") or error_data.get("message", str(response.status_code)))
        
        return response.json()
    
    def sign_in(self, email: str, password: str) -> Dict:
        """Sign in a user via Supabase Auth"""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        response = httpx.post(
            self._auth_url("token?grant_type=password"),
            headers=self._get_headers(),
            json={"email": email, "password": password},
            timeout=30
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.text else {"message": "Unknown error"}
            raise Exception(error_data.get("error_description") or error_data.get("message", "Invalid credentials"))
        
        return response.json()
    
    # ============================================
    # USER & TENANT OPERATIONS
    # ============================================
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile including tenant_id"""
        if not self.client:
            return None
        
        response = httpx.get(
            f"{self._rest_url('user_profiles')}?id=eq.{user_id}",
            headers=self._get_headers(use_service_key=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None
    
    def create_user_profile(self, user_id: str, email: str, full_name: str) -> Dict:
        """Create user profile with auto-generated tenant_id"""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        response = httpx.post(
            self._rest_url('user_profiles'),
            headers=self._get_headers(use_service_key=True),
            json={"id": user_id, "full_name": full_name},
            timeout=10
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create profile: {response.text}")
        
        data = response.json()
        return data[0] if isinstance(data, list) else data
    
    def update_user_profile(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """Update user profile - used to sync tenant_id back to Supabase"""
        if not self.client:
            return None
        
        response = httpx.patch(
            f"{self._rest_url('user_profiles')}?id=eq.{user_id}",
            headers=self._get_headers(use_service_key=True),
            json=updates,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            data = response.json() if response.text else {}
            return data[0] if isinstance(data, list) and data else updates
        
        print(f"Failed to update user profile: {response.status_code} - {response.text}")
        return None
    
    def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict]:
        """Lookup user by tenant_id"""
        if not self.client:
            return None
        
        response = httpx.get(
            f"{self._rest_url('user_profiles')}?tenant_id=eq.{tenant_id}",
            headers=self._get_headers(use_service_key=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None

    def get_tenant_by_email(self, email: str) -> Optional[Dict]:
        """SELECT * FROM tenant_config WHERE user_email = email LIMIT 1"""
        if not self.client:
            return None
        response = httpx.get(
            f"{self._rest_url('tenant_config')}?user_email=eq.{email}&limit=1",
            headers=self._get_headers(use_service_key=True),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None

    def get_tenant_by_phone(self, phone: str) -> Optional[Dict]:
        """SELECT * FROM tenant_config WHERE whatsapp_number = phone LIMIT 1"""
        if not self.client:
            return None
        response = httpx.get(
            f"{self._rest_url('tenant_config')}?whatsapp_number=eq.{phone}&limit=1",
            headers=self._get_headers(use_service_key=True),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None
    
    def create_tenant_config(self, tenant_id: str, email: str, company_name: str, whatsapp_number: Optional[str] = None) -> Optional[Dict]:
        """Create a default trial configuration in tenant_config table"""
        if not self.client:
            return None
            
        from datetime import datetime, timezone, timedelta
        trial_ends_at = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        
        payload = {
            "tenant_id": tenant_id,
            "user_email": email,
            "company_name": company_name,
            "whatsapp_number": whatsapp_number,
            "subscription_status": "trial",
            "trial_ends_at": trial_ends_at
        }
        
        try:
            response = httpx.post(
                self._rest_url('tenant_config'),
                headers=self._get_headers(use_service_key=True),
                json=payload,
                timeout=10
            )
            if response.status_code in [200, 201]:
                data = response.json() if response.text else [payload]
                return data[0] if isinstance(data, list) and data else payload
            print(f"Failed to create tenant config: {response.text}")
            return None
        except Exception as e:
            print(f"Error creating tenant config: {e}")
            return None
    
    # ============================================
    # SUBSCRIPTION OPERATIONS
    # ============================================
    
    def get_user_subscription(self, user_id: str) -> Optional[Dict]:
        """Get active subscription for user"""
        if not self.client:
            return None
        
        response = httpx.get(
            f"{self._rest_url('subscriptions')}?user_id=eq.{user_id}&status=eq.active&order=created_at.desc&limit=1",
            headers=self._get_headers(use_service_key=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None
    
    def create_subscription(self, user_id: str, tenant_id: str, plan: str = "free") -> Dict:
        """Create a subscription for a user"""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        response = httpx.post(
            self._rest_url('subscriptions'),
            headers=self._get_headers(use_service_key=True),
            json={
                "user_id": user_id,
                "tenant_id": tenant_id,
                "plan": plan,
                "status": "active",
                "device_limit": 1
            },
            timeout=10
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create subscription: {response.text}")
        
        data = response.json()
        return data[0] if isinstance(data, list) else data
    
    def check_subscription_valid(self, user_id: str) -> bool:
        """Check if user has valid active subscription"""
        sub = self.get_user_subscription(user_id)
        
        if not sub:
            return False
        
        if sub.get('status') != 'active':
            return False
        
        if sub.get('valid_until'):
            from datetime import datetime
            valid_until = datetime.fromisoformat(sub['valid_until'].replace('Z', '+00:00'))
            if datetime.utcnow() > valid_until.replace(tzinfo=None):
                return False
        
        return True
    
    # ============================================
    # DEVICE LICENSE OPERATIONS
    # ============================================
    
    def register_device(self, user_id: str, tenant_id: str, device_fingerprint: str, device_name: str) -> Dict:
        """Register new device for user"""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        license_key = f"LIC-{uuid.uuid4().hex[:16].upper()}"
        
        response = httpx.post(
            self._rest_url('device_licenses'),
            headers=self._get_headers(use_service_key=True),
            json={
                "license_key": license_key,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "device_fingerprint": device_fingerprint,
                "device_name": device_name,
                "status": "active"
            },
            timeout=10
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to register device: {response.text}")
        
        data = response.json()
        return data[0] if isinstance(data, list) else data
    
    def validate_license(self, device_fingerprint: str) -> bool:
        """Check if device license is valid"""
        if not self.client:
            return False
        
        response = httpx.get(
            f"{self._rest_url('device_licenses')}?device_fingerprint=eq.{device_fingerprint}&status=eq.active",
            headers=self._get_headers(use_service_key=True),
            timeout=10
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        return False


# Global instance - use this in place of supabase_service
supabase_http_service = SupabaseHTTPService()


# Compatibility wrapper - makes old code work with new HTTP service
class SupabaseService:
    """
    Compatibility wrapper that makes the HTTP service look like the old client-based service.
    This allows existing code to work without modification.
    """
    
    def __init__(self):
        self._http = supabase_http_service
        # Fake client attribute for compatibility checks
        self.client = True if self._http.client else None
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        return self._http.get_user_profile(user_id)
    
    def create_user_profile(self, user_id: str, email: str, full_name: str) -> Dict:
        return self._http.create_user_profile(user_id, email, full_name)
    
    def update_user_profile(self, user_id: str, updates: Dict) -> Optional[Dict]:
        return self._http.update_user_profile(user_id, updates)
    
    def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict]:
        return self._http.get_tenant_by_id(tenant_id)

    def get_tenant_by_email(self, email: str) -> Optional[Dict]:
        return self._http.get_tenant_by_email(email)

    def get_tenant_by_phone(self, phone: str) -> Optional[Dict]:
        return self._http.get_tenant_by_phone(phone)

    def create_tenant_config(self, tenant_id: str, email: str, company_name: str, whatsapp_number: Optional[str] = None) -> Optional[Dict]:
        return self._http.create_tenant_config(tenant_id, email, company_name, whatsapp_number)
    
    def get_user_subscription(self, user_id: str) -> Optional[Dict]:
        return self._http.get_user_subscription(user_id)
    
    def check_subscription_valid(self, user_id: str) -> bool:
        return self._http.check_subscription_valid(user_id)
    
    def register_device(self, user_id: str, tenant_id: str, device_fingerprint: str, device_name: str) -> Dict:
        return self._http.register_device(user_id, tenant_id, device_fingerprint, device_name)
    
    def validate_license(self, device_fingerprint: str) -> bool:
        return self._http.validate_license(device_fingerprint)


# Global instance for backward compatibility
supabase_service = SupabaseService()
