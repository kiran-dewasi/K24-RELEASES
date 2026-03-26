"""
K24 Cloud Backend Services

Cloud-safe service surface only. Local-only services (bulk_processor,
export_service, query_orchestrator, tenant_service, etc.) must never
be imported here. Import them directly in local/Tauri routers only.
"""

from services.supabase_service import (
    SupabaseHTTPService,
    SupabaseService,
    supabase_http_service,
    supabase_service,
)

__all__ = [
    "SupabaseHTTPService",
    "SupabaseService",
    "supabase_http_service",
    "supabase_service",
]
