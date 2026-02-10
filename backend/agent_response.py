# K24 AI Agent - Response Formatter
# ==================================
# Formats agent outputs for frontend consumption

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ResponseType(Enum):
    """Types of responses"""
    SUCCESS = "success"
    ERROR = "error"
    PREVIEW = "preview"
    NAVIGATION = "navigation"
    CLARIFICATION = "clarification"
    PROGRESS = "progress"


def format_success_response(
    transaction_id: str,
    message: str,
    details: Dict[str, Any],
    audit_trail: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format a successful transaction response.
    
    Example:
    {
      "status": "SUCCESS",
      "type": "success",
      "transaction_id": "TXN_20251202_001",
      "message": "Invoice created successfully",
      "details": {
        "customer": "HDFC Bank",
        "amount": "₹59,000",
        "date": "2025-12-02"
      },
      "audit_trail": {
        "created_by": "KITTU",
        "timestamp": "2025-12-02T00:15:30Z"
      }
    }
    """
    return {
        "status": "SUCCESS",
        "type": ResponseType.SUCCESS.value,
        "transaction_id": transaction_id,
        "message": message,
        "details": details,
        "audit_trail": audit_trail or {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def format_error_response(
    error_code: str,
    message: str,
    suggestions: List[str] = None,
    retry_available: bool = False,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format an error response.
    
    Example:
    {
      "status": "FAILED",
      "type": "error",
      "error_code": "LEDGER_NOT_FOUND",
      "message": "Ledger 'HDFC Bank' not found",
      "suggestions": [
        "Check spelling",
        "Create ledger in Tally first"
      ],
      "retry_available": true
    }
    """
    return {
        "status": "FAILED",
        "type": ResponseType.ERROR.value,
        "error_code": error_code,
        "message": message,
        "suggestions": suggestions or [],
        "retry_available": retry_available,
        "context": context or {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def format_preview_response(
    transaction_id: str,
    preview_data: Dict[str, Any],
    risk_level: str = "LOW",
    warnings: List[str] = None,
    estimated_completion_time: int = 3
) -> Dict[str, Any]:
    """
    Format a transaction preview response (awaiting approval).
    
    Example:
    {
      "status": "AWAITING_APPROVAL",
      "type": "preview",
      "transaction_id": "TXN_20251202_001",
      "message": "Please review and approve",
      "preview": {
        "customer": "HDFC Bank",
        "amount": "₹59,000",
        "tax": "₹9,000",
        "total": "₹59,000"
      },
      "risk_level": "LOW",
      "warnings": [],
      "actions": [
        {"label": "Approve", "action": "approve", "style": "primary"},
        {"label": "Edit", "action": "edit", "style": "secondary"},
        {"label": "Cancel", "action": "cancel", "style": "danger"}
      ]
    }
    """
    return {
        "status": "AWAITING_APPROVAL",
        "type": ResponseType.PREVIEW.value,
        "transaction_id": transaction_id,
        "message": "Please review and approve this transaction",
        "preview": preview_data,
        "risk_level": risk_level,
        "warnings": warnings or [],
        "estimated_completion_time_seconds": estimated_completion_time,
        "actions": [
            {"label": "Approve", "action": "approve", "style": "primary"},
            {"label": "Edit", "action": "edit", "style": "secondary"},
            {"label": "Cancel", "action": "cancel", "style": "danger"}
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def format_navigation_response(
    path: str,
    message: str,
    pre_filled_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format a navigation response (redirect to a page).
    
    Example:
    {
      "status": "NAVIGATION",
      "type":  "navigation",
      "message": "Opening receipt form...",
      "path": "/vouchers/new/receipt?party=HDFC+Bank&amount=50000",
      "pre_filled_data": {"party": "HDFC Bank", "amount": 50000}
    }
    """
    return {
        "status": "NAVIGATION",
        "type": ResponseType.NAVIGATION.value,
        "message": message,
        "path": path,
        "pre_filled_data": pre_filled_data or {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def format_clarification_response(
    message: str,
    question: str,
    options: List[str] = None,
    missing_fields: List[str] = None
) -> Dict[str, Any]:
    """
    Format a clarification request (need more info from user).
    
    Example:
    {
      "status": "NEEDS_CLARIFICATION",
      "type": "clarification",
      "message": "I need more information",
      "question": "Which party is this for?",
      "options": ["HDFC Bank", "ICICI Bank", "SBI"],
      "missing_fields": ["party_name"]
    }
    """
    return {
        "status": "NEEDS_CLARIFICATION",
        "type": ResponseType.CLARIFICATION.value,
        "message": message,
        "question": question,
        "options": options or [],
        "missing_fields": missing_fields or [],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def format_progress_response(
    message: str,
    current_step: str,
    total_steps: int,
    current_step_number: int
) -> Dict[str, Any]:
    """
    Format a progress update response (long-running operation).
    
    Example:
    {
      "status": "PROCESSING",
      "type": "progress",
      "message": "Generating XML...",
      "progress": {
        "current_step": "generate_xml",
        "current_step_number": 3,
        "total_steps": 7,
        "percentage": 42
      }
    }
    """
    percentage = int((current_step_number / total_steps) * 100)
    
    return {
        "status": "PROCESSING",
        "type": ResponseType.PROGRESS.value,
        "message": message,
        "progress": {
            "current_step": current_step,
            "current_step_number": current_step_number,
            "total_steps": total_steps,
            "percentage": percentage
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def format_agent_response(agent_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-detect type and format agent output appropriately.
    """
    
    status = agent_output.get("status", "").upper()
    
    if status == "SUCCESS":
        return format_success_response(
            transaction_id=agent_output.get("transaction_id"),
            message=agent_output.get("message"),
            details=agent_output.get("details", {}),
            audit_trail=agent_output.get("audit_trail")
        )
    
    elif status == "FAILED":
        errors = agent_output.get("errors", [])
        first_error = errors[0] if errors else {}
        
        return format_error_response(
            error_code=first_error.get("code", "UNKNOWN_ERROR"),
            message=first_error.get("message", agent_output.get("message", "Unknown error")),
            suggestions=first_error.get("suggestions", []),
            retry_available=first_error.get("retry_available", False),
            context=first_error.get("context")
        )
    
    elif status == "AWAITING_APPROVAL":
        return format_preview_response(
            transaction_id=agent_output.get("transaction_id"),
            preview_data=agent_output.get("preview", {}),
            risk_level=agent_output.get("risk_level", "LOW"),
            warnings=agent_output.get("warnings", [])
        )
    
    elif status == "NAVIGATION":
        return format_navigation_response(
            path=agent_output.get("path"),
            message=agent_output.get("message"),
            pre_filled_data=agent_output.get("pre_filled_data")
        )
    
    elif status == "NEEDS_CLARIFICATION":
        return format_clarification_response(
            message=agent_output.get("message"),
            question=agent_output.get("question"),
            options=agent_output.get("options"),
            missing_fields=agent_output.get("missing_fields")
        )
    
    elif status == "PROCESSING":
        return format_progress_response(
            message=agent_output.get("message"),
            current_step=agent_output.get("current_step"),
            total_steps=agent_output.get("total_steps", 7),
            current_step_number=agent_output.get("current_step_number", 1)
        )
    
    else:
        # Unknown status, return as-is with type
        return {
            **agent_output,
            "type": "unknown",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


# Example usage
if __name__ == "__main__":
    import json
    
    # Test success response
    success = format_success_response(
        transaction_id="TXN_20251202_001",
        message="Invoice created successfully",
        details={
            "customer": "HDFC Bank",
            "amount": "₹59,000",
            "date": "2025-12-02",
            "invoice_number": "INV-001"
        },
        audit_trail={
            "created_by": "KITTU",
            "timestamp": "2025-12-02T00:15:30Z"
        }
    )
    print("SUCCESS Response:")
    print(json.dumps(success, indent=2))
    
    # Test error response
    error = format_error_response(
        error_code="LEDGER_NOT_FOUND",
        message="Ledger 'HDFC Bank' not found in Tally",
        suggestions=[
            "Check spelling and try again",
            "Create the ledger in Tally first"
        ],
        retry_available=True
    )
    print("\nERROR Response:")
    print(json.dumps(error, indent=2))
    
    # Test preview response
    preview = format_preview_response(
        transaction_id="TXN_20251202_002",
        preview_data={
            "customer": "HDFC Bank",
            "amount": "₹59,000",
            "tax": "₹9,000",
            "total": "₹59,000",
            "date": "2025-12-02"
        },
        risk_level="LOW",
        warnings=[]
    )
    print("\nPREVIEW Response:")
    print(json.dumps(preview, indent=2))
