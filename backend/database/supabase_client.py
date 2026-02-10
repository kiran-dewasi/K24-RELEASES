"""
Safe Supabase Client - Uses HTTP instead of the official supabase-py library
This avoids the pyiceberg dependency issue
"""
import os
import httpx
from typing import Optional, Any, Dict, List

class SafeSupabaseClient:
    """
    HTTP-based Supabase client that doesn't require the full supabase-py library.
    Supports both old JWT format and new sb_publishable_ format keys.
    """
    def __init__(self):
        self.enabled = os.getenv("K24_DISABLE_SUPABASE", "false").lower() != "true"
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.client: Optional[Any] = None
        
        if self.enabled and self.url and self.key:
            self.client = True  # Flag indicating client is configured
        else:
            if not self.url or not self.key:
                print("[WARNING] Supabase credentials missing, running in local mode")
            self.enabled = False
    
    def _get_headers(self, use_service_key: bool = False) -> Dict[str, str]:
        """Get headers for Supabase API calls"""
        key = self.service_key if use_service_key and self.service_key else self.key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def _rest_url(self, table_name: str) -> str:
        """Get REST API URL for a table"""
        return f"{self.url}/rest/v1/{table_name}"
    
    def table(self, table_name: str):
        if not self.enabled or not self.client:
            return MockTable(table_name)
        return HTTPTable(self, table_name)


class HTTPTable:
    """HTTP-based table operations"""
    def __init__(self, client: SafeSupabaseClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self._filters = []
        self._order_by = None
        self._limit_val = None
    
    def insert(self, data: Dict) -> 'HTTPQuery':
        return HTTPQuery(self.client, self.table_name, "INSERT", data)
    
    def upsert(self, data: Dict) -> 'HTTPQuery':
        return HTTPQuery(self.client, self.table_name, "UPSERT", data)
    
    def select(self, *args) -> 'HTTPQuery':
        columns = ",".join(args) if args else "*"
        return HTTPQuery(self.client, self.table_name, "SELECT", columns=columns)
    
    def update(self, data: Dict) -> 'HTTPQuery':
        return HTTPQuery(self.client, self.table_name, "UPDATE", data)
    
    def delete(self) -> 'HTTPQuery':
        return HTTPQuery(self.client, self.table_name, "DELETE")


class HTTPQuery:
    """Chainable HTTP query builder"""
    def __init__(self, client: SafeSupabaseClient, table_name: str, operation: str, 
                 data: Any = None, columns: str = "*"):
        self.client = client
        self.table_name = table_name
        self.operation = operation
        self.data = data
        self.columns = columns
        self._filters: List[str] = []
        self._order_by: Optional[str] = None
        self._limit_val: Optional[int] = None
    
    def eq(self, column: str, value: Any) -> 'HTTPQuery':
        self._filters.append(f"{column}=eq.{value}")
        return self
    
    def neq(self, column: str, value: Any) -> 'HTTPQuery':
        self._filters.append(f"{column}=neq.{value}")
        return self
    
    def order(self, column: str, desc: bool = False) -> 'HTTPQuery':
        self._order_by = f"{column}.{'desc' if desc else 'asc'}"
        return self
    
    def limit(self, count: int) -> 'HTTPQuery':
        self._limit_val = count
        return self
    
    def execute(self) -> Any:
        """Execute the query and return results"""
        try:
            url = self.client._rest_url(self.table_name)
            headers = self.client._get_headers(use_service_key=True)
            
            # Build query string
            params = []
            if self.operation == "SELECT":
                params.append(f"select={self.columns}")
            
            params.extend(self._filters)
            
            if self._order_by:
                params.append(f"order={self._order_by}")
            
            if self._limit_val:
                params.append(f"limit={self._limit_val}")
            
            if params:
                url += "?" + "&".join(params)
            
            # Execute based on operation
            if self.operation == "SELECT":
                response = httpx.get(url, headers=headers, timeout=10)
            elif self.operation == "INSERT":
                response = httpx.post(
                    self.client._rest_url(self.table_name),
                    headers=headers,
                    json=self.data,
                    timeout=10
                )
            elif self.operation == "UPSERT":
                headers["Prefer"] = "resolution=merge-duplicates,return=representation"
                response = httpx.post(
                    self.client._rest_url(self.table_name),
                    headers=headers,
                    json=self.data,
                    timeout=10
                )
            elif self.operation == "UPDATE":
                filter_url = self.client._rest_url(self.table_name)
                if self._filters:
                    filter_url += "?" + "&".join(self._filters)
                response = httpx.patch(filter_url, headers=headers, json=self.data, timeout=10)
            elif self.operation == "DELETE":
                filter_url = self.client._rest_url(self.table_name)
                if self._filters:
                    filter_url += "?" + "&".join(self._filters)
                response = httpx.delete(filter_url, headers=headers, timeout=10)
            else:
                return type('obj', (object,), {'data': []})()
            
            # Return result
            if response.status_code in [200, 201]:
                return type('obj', (object,), {'data': response.json()})()
            else:
                print(f"[SUPABASE] {self.operation} failed: {response.status_code} - {response.text[:200]}")
                return type('obj', (object,), {'data': []})()
                
        except Exception as e:
            print(f"[SUPABASE] {self.operation} error: {e}")
            return type('obj', (object,), {'data': []})()


class MockTable:
    """No-op implementation for when Supabase is disabled"""
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    def insert(self, data):
        print(f"[DISABLED] Supabase disabled: Skipping insert to {self.table_name}")
        return MockQuery()
    
    def upsert(self, data):
        print(f"[DISABLED] Supabase disabled: Skipping upsert to {self.table_name}")
        return MockQuery()

    def select(self, *args):
        print(f"[DISABLED] Supabase disabled: Returning empty result for {self.table_name}")
        return MockQuery()
    
    def update(self, data):
        print(f"[DISABLED] Supabase disabled: Skipping update to {self.table_name}")
        return MockQuery()
    
    def delete(self):
        print(f"[DISABLED] Supabase disabled: Skipping delete to {self.table_name}")
        return MockQuery()


class MockQuery:
    def execute(self):
        return type('obj', (object,), {'data': []})()
    
    def eq(self, *args):
        return self
    
    def neq(self, *args):
        return self
    
    def order(self, *args, **kwargs):
        return self
        
    def limit(self, *args):
        return self


# Global instance
supabase = SafeSupabaseClient()
