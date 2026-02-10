"""
Query API Router - Day 5 Smart Query Endpoint
==============================================
API endpoint for processing natural language queries via WhatsApp or Web.
Returns text responses and optional file exports (PDF/Excel).
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import logging
import os

from backend.database import get_db
from backend.auth import get_current_tenant_id
from backend.services.query_orchestrator import (
    QueryOrchestrator,
    process_user_query,
    QueryIntent
)

logger = logging.getLogger("query_api")

router = APIRouter(prefix="/query", tags=["Smart Query"])


# ============== Request/Response Models ==============

class QueryRequest(BaseModel):
    """Request model for natural language query"""
    query: str = Field(..., description="Natural language query from user", min_length=1)
    context: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional context (e.g., previous conversation, user preferences)"
    )
    format: Optional[str] = Field(
        default="text", 
        description="Response format: 'text', 'json', or 'file'"
    )


class QueryResponse(BaseModel):
    """Response model for query results"""
    success: bool
    intent: str
    confidence: float
    response_text: str
    data: Dict[str, Any]
    has_file: bool = False
    file_path: Optional[str] = None
    filename: Optional[str] = None
    suggestions: List[str] = []


class SupportedQueriesResponse(BaseModel):
    """Response showing supported query types"""
    categories: Dict[str, List[str]]


# ============== Endpoints ==============

@router.post("/ask", response_model=QueryResponse)
async def ask_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    🧠 Process a natural language query and return smart response.
    
    This is the main endpoint for the Day 5 "Smart Query" feature.
    Users can ask questions in natural language and get:
    - Concise text responses (for WhatsApp)
    - Data in JSON format
    - PDF/Excel files when requested
    
    Example queries:
    - "How much does ABC Corp owe?"
    - "January sales summary"
    - "Stock of Product A"
    - "Export sales to Excel"
    - "Send invoice INV-001 as PDF"
    """
    try:
        orchestrator = QueryOrchestrator(db, tenant_id)
        
        # Parse and process the query
        parsed = orchestrator.parse_query(request.query)
        result = orchestrator.process_query(request.query)
        
        # Build suggestions based on intent
        suggestions = _get_follow_up_suggestions(parsed.intent, result.data)
        
        return QueryResponse(
            success=result.success,
            intent=parsed.intent.value,
            confidence=parsed.confidence,
            response_text=result.formatted_response,
            data=result.data,
            has_file=result.export_file is not None,
            file_path=result.export_file,
            filename=os.path.basename(result.export_file) if result.export_file else None,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_export_file(
    filename: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    📥 Download an exported PDF/Excel file.
    
    After generating a report via /ask, use this endpoint to download the file.
    """
    # Get exports directory
    from backend.services.export_service import get_exports_dir
    exports_dir = get_exports_dir()
    
    file_path = exports_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    
    # Determine media type
    if filename.endswith('.pdf'):
        media_type = "application/pdf"
    elif filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


@router.get("/supported", response_model=SupportedQueriesResponse)
async def get_supported_queries():
    """
    📋 Get list of supported query types with examples.
    
    Returns categorized examples of what users can ask.
    """
    return SupportedQueriesResponse(
        categories={
            "Outstanding & Payments": [
                "How much does ABC Corp owe?",
                "Outstanding from XYZ Industries",
                "ABC Corp payment history this month",
                "Show overall outstanding",
            ],
            "Stock & Inventory": [
                "Stock of Product A",
                "What's the rate of Product B?",
                "Inventory summary",
                "Low stock items",
            ],
            "Sales & Purchases": [
                "January sales summary",
                "This month's sales",
                "Purchase summary last month",
                "Top 10 customers by sales",
            ],
            "Reports & Exports": [
                "Export January sales to Excel",
                "Send invoice INV-001 as PDF",
                "ABC Corp statement PDF",
                "Stock report Excel",
            ],
            "Invoices & Vouchers": [
                "Show invoice INV-001",
                "Last 5 sales",
                "Recent purchase vouchers",
            ],
            "Cash & Balance": [
                "Cash balance today",
                "Cash book status",
            ],
        }
    )


@router.post("/whatsapp")
async def process_whatsapp_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    📱 Special endpoint for WhatsApp queries from Baileys listener.
    
    Optimized for WhatsApp responses:
    - Returns shorter, emoji-rich text
    - Handles file generation and returns path for Baileys to send
    - Uses Baileys secret for authentication (not JWT)
    
    Note: This endpoint is called by the Baileys listener which uses
    X-Baileys-Secret header for authentication. The tenant_id is resolved
    from the context passed in the request.
    """
    try:
        # Get tenant_id from context or use default
        # In production, resolve tenant from sender phone via user lookup
        tenant_id = "default"
        if request.context:
            tenant_id = request.context.get("resolved_user_id") or request.context.get("tenant_id") or "default"
        
        orchestrator = QueryOrchestrator(db, tenant_id)
        result = orchestrator.process_query(request.query)
        
        response = {
            "success": result.success,
            "message": result.formatted_response,
            "has_file": result.export_file is not None,
        }
        
        if result.export_file:
            response["file"] = {
                "path": result.export_file,
                "filename": os.path.basename(result.export_file),
                "type": "pdf" if result.export_file.endswith('.pdf') else "excel"
            }
        
        return response
        
    except Exception as e:
        import traceback
        logger.error(f"WhatsApp query processing failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"QUERY ERROR: {e}")
        print(traceback.format_exc())
        return {
            "success": False,
            "message": "❌ Sorry, I couldn't process that request. Please try again.",
            "has_file": False
        }


# ============== Helper Functions ==============

def _get_follow_up_suggestions(intent: QueryIntent, data: Dict[str, Any]) -> List[str]:
    """Generate follow-up suggestions based on the query result"""
    suggestions = []
    
    if intent == QueryIntent.OUTSTANDING:
        party_name = data.get("party_name")
        if party_name:
            suggestions = [
                f"Payment history of {party_name}",
                f"Send {party_name} statement as PDF",
                "Show overall outstanding"
            ]
        else:
            suggestions = [
                "Outstanding from [party name]",
                "Export outstanding to Excel"
            ]
    
    elif intent == QueryIntent.SALES_SUMMARY:
        suggestions = [
            "Export sales to Excel",
            "Top 10 customers",
            "Compare with last month"
        ]
    
    elif intent == QueryIntent.STOCK_CHECK:
        item_name = data.get("item_name")
        if item_name:
            suggestions = [
                f"Rate of {item_name}",
                f"Who buys {item_name} most?",
                "Export stock report"
            ]
        else:
            suggestions = [
                "Stock of [item name]",
                "Low stock items"
            ]
    
    elif intent == QueryIntent.INVOICE_DETAILS:
        voucher_number = data.get("voucher_number")
        if voucher_number:
            suggestions = [
                f"Send {voucher_number} as PDF",
                "Last 5 sales"
            ]
    
    elif intent == QueryIntent.GENERAL_QUERY:
        suggestions = [
            "Show outstanding",
            "This month's sales",
            "Stock summary"
        ]
    
    return suggestions[:3]  # Max 3 suggestions
