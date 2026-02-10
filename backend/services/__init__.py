"""
K24 Backend Services

Centralized business logic services.
"""

from backend.services.ledger_service import LedgerService, get_or_create_ledger
from backend.services.bulk_processor import BulkBillProcessor, bulk_processor
from backend.services.confidence_scorer import (
    calculate_overall_confidence,
    identify_uncertain_fields,
    generate_clarification_question,
    get_confidence_summary
)
from backend.services.auto_executor import (
    process_with_auto_execution,
    process_with_auto_execution_sync,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD
)
from backend.services.tally_sync_service import (
    tally_sync_service,
    start_sync_service,
    stop_sync_service,
    sync_now,
    get_sync_status
)
from backend.services.query_orchestrator import (
    QueryOrchestrator,
    process_user_query,
    ParsedQuery,
    OrchestrationResult,
    QueryIntent
)
from backend.services.export_service import (
    ExportService,
    PDFGenerator,
    ExcelGenerator,
    export_invoice_to_pdf,
    export_statement_to_pdf,
    export_sales_to_excel
)
from backend.services.tenant_service import (
    TenantService,
    tenant_service
)

__all__ = [
    # Ledger
    'LedgerService', 
    'get_or_create_ledger',
    # Bulk processing
    'BulkBillProcessor',
    'bulk_processor',
    # Confidence scoring
    'calculate_overall_confidence',
    'identify_uncertain_fields',
    'generate_clarification_question',
    'get_confidence_summary',
    # Auto-execution
    'process_with_auto_execution',
    'process_with_auto_execution_sync',
    'HIGH_CONFIDENCE_THRESHOLD',
    'MEDIUM_CONFIDENCE_THRESHOLD',
    # Tally Sync Service
    'tally_sync_service',
    'start_sync_service',
    'stop_sync_service',
    'sync_now',
    'get_sync_status',
    # Query Orchestrator
    'QueryOrchestrator',
    'process_user_query',
    'ParsedQuery',
    'OrchestrationResult',
    'QueryIntent',
    # Export Service
    'ExportService',
    'PDFGenerator',
    'ExcelGenerator',
    'export_invoice_to_pdf',
    'export_statement_to_pdf',
    'export_sales_to_excel',
    # Tenant Service (Phase 1)
    'TenantService',
    'tenant_service',
]

