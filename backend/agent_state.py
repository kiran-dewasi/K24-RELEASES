# K24 AI Agent - State Definitions for LangGraph
# ===============================================

from typing import TypedDict, List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStateEnum(Enum):
    """Possible states in the agent workflow"""
    PARSE_INTENT = "parse_intent"
    VALIDATE_PARAMS = "validate_params"
    GENERATE_XML = "generate_xml"
    VALIDATE_XML = "validate_xml"
    DRY_RUN = "dry_run"
    AWAIT_APPROVAL = "await_approval"
    EXECUTE_TALLY = "execute_tally"
    VERIFY = "verify"
    RESPOND = "respond"
    ERROR = "error"


class TransactionStatus(Enum):
    """Status of the transaction"""
    PENDING = "pending"
    VALIDATING = "validating"
    GENERATING = "generating"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentState(TypedDict, total=False):
    """
    Comprehensive state object that flows through the LangGraph.
    All components read from and write to this state.
    """
    # Input
    user_message: str
    user_id: str
    company_name: str
    transaction_id: str
    
    # Intent Classification
    intent: Optional[str]
    intent_confidence: float
    raw_parameters: Dict[str, Any]
    
    # Validation
    validated_parameters: Dict[str, Any]
    validation_errors: List[Dict[str, Any]]
    validation_warnings: List[str]
    validation_confidence: float
    is_valid: bool
    
    # XML Generation
    generated_xml: Optional[str]
    generated_answer: Optional[str]
    xml_validation_errors: List[str]
    xml_generation_attempts: int
    
    # Dry Run / Preview
    transaction_preview: Dict[str, Any]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    requires_approval: bool
    
    # Approval
    approved: Optional[bool]
    approval_timestamp: Optional[str]
    
    # Execution
    tally_response: Optional[Dict[str, Any]]
    tally_reference: Optional[str]
    execution_timestamp: Optional[str]
    
    # Verification
    verified: bool
    verification_details: Dict[str, Any]
    
    # Response
    status: TransactionStatus
    final_response: Dict[str, Any]
    
    # Error Handling
    errors: List[Dict[str, Any]]
    retry_count: int
    max_retries: int
    
    # Audit Trail
    audit_log: List[Dict[str, Any]]
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    
    # Context
    tally_url: str
    tally_edu_mode: bool
    ledger_cache: Optional[Any]


@dataclass
class StateUpdate:
    """Helper class for updating state with audit logging"""
    field: str
    value: Any
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_audit_entry(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "field": self.field,
            "message": self.message,
            "value": str(self.value)[:200]  # Truncate long values
        }


def create_initial_state(
    user_message: str,
    user_id: str,
    company_name: str,
    tally_url: str = "http://localhost:9000",
    tally_edu_mode: bool = True
) -> AgentState:
    """Create initial state for a new agent request"""
    
    transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return AgentState(
        # Input
        user_message=user_message,
        user_id=user_id,
        company_name=company_name,
        transaction_id=transaction_id,
        tally_url=tally_url,
        tally_edu_mode=tally_edu_mode,
        
        # Initial values
        intent=None,
        intent_confidence=0.0,
        raw_parameters={},
        validated_parameters={},
        validation_errors=[],
        validation_warnings=[],
        validation_confidence=0.0,
        is_valid=False,
        generated_xml=None,
        xml_validation_errors=[],
        xml_generation_attempts=0,
        transaction_preview={},
        risk_level="LOW",
        requires_approval=False,
        approved=None,
        approval_timestamp=None,
        tally_response=None,
        tally_reference=None,
        execution_timestamp=None,
        verified=False,
        verification_details={},
        status=TransactionStatus.PENDING,
        final_response={},
        errors=[],
        retry_count=0,
        max_retries=3,
        audit_log=[],
        started_at=datetime.utcnow().isoformat() + "Z",
        completed_at=None,
        duration_ms=None,
        ledger_cache=None
    )


def update_state_with_audit(
    state: AgentState,
    updates: Dict[str, Any],
    message: str
) -> AgentState:
    """
    Update state and add to audit log.
    Returns new state (functional style for LangGraph).
    """
    # Create new state with updates
    new_state = {**state, **updates}
    
    # Add audit entry
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message,
        "updates": list(updates.keys())
    }
    
    new_state["audit_log"] = state.get("audit_log", []) + [audit_entry]
    
    return new_state


def add_error_to_state(
    state: AgentState,
    error_code: str,
    error_message: str,
    severity: str = "MEDIUM",
    suggestions: List[str] = None
) -> AgentState:
    """Add an error to the state"""
    
    error = {
        "code": error_code,
        "message": error_message,
        "severity": severity,
        "suggestions": suggestions or [],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    new_errors = state.get("errors", []) + [error]
    
    return update_state_with_audit(
        state,
        {
            "errors": new_errors,
            "status": TransactionStatus.FAILED
        },
        f"Error added: {error_code}"
    )


def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """Get a concise summary of current state (for logging/debugging)"""
    return {
        "transaction_id": state.get("transaction_id"),
        "status": state.get("status", TransactionStatus.PENDING).value if isinstance(state.get("status"), TransactionStatus) else state.get("status"),
        "intent": state.get("intent"),
        "is_valid": state.get("is_valid"),
        "approved": state.get("approved"),
        "has_errors": len(state.get("errors", [])) > 0,
        "retry_count": state.get("retry_count", 0),
        "duration_ms": state.get("duration_ms")
    }
