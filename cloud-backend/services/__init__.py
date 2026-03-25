"""
K24 Backend Services

Centralized business logic services.
"""

from services.supabase_service import (
    SupabaseHTTPService,
    SupabaseService,
    supabase_http_service,
    supabase_service,
)
from services.tenant_service import TenantService, tenant_service
from services.bulk_processor import BulkBillProcessor, bulk_processor
from services.query_orchestrator import (
    OrchestrationResult,
    ParsedQuery,
    QueryIntent,
    QueryOrchestrator,
    process_user_query,
)
from services.export_service import (
    ExcelGenerator,
    ExportService,
    PDFGenerator,
    export_invoice_to_pdf,
    export_sales_to_excel,
    export_statement_to_pdf,
)

__all__ = [
    # Supabase
    "SupabaseHTTPService",
    "SupabaseService",
    "supabase_http_service",
    "supabase_service",
    # Tenant Service
    "TenantService",
    "tenant_service",
    # Bulk processing
    "BulkBillProcessor",
    "bulk_processor",
    # Query Orchestrator
    "OrchestrationResult",
    "ParsedQuery",
    "QueryIntent",
    "QueryOrchestrator",
    "process_user_query",
    # Export Service
    "ExcelGenerator",
    "ExportService",
    "PDFGenerator",
    "export_invoice_to_pdf",
    "export_sales_to_excel",
    "export_statement_to_pdf",
]
