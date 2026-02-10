# K24 AI Agent - Error Types and Handling System
# ==============================================

from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels for K24 Agent"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors in K24 system"""
    VALIDATION = "validation"  # User input issues
    SYSTEM = "system"  # Our infrastructure issues
    FINANCIAL = "financial"  # High-risk financial operations
    TALLY_CONNECTION = "tally_connection"  # Tally connectivity issues
    GEMINI_API = "gemini_api"  # Gemini API issues


class K24ErrorCode(Enum):
    """Comprehensive error codes for K24 operations"""
    
    # --- CATEGORY 1: SYSTEM ERRORS (503) ---
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    TALLY_CONNECTION_FAILED = "TALLY_CONNECTION_FAILED"
    GEMINI_API_TIMEOUT = "GEMINI_API_TIMEOUT"
    GEMINI_API_RATE_LIMIT = "GEMINI_API_RATE_LIMIT"
    GEMINI_API_AUTH_FAILED = "GEMINI_API_AUTH_FAILED"
    GEMINI_API_ERROR = "GEMINI_API_ERROR"
    REDIS_CONNECTION_FAILED = "REDIS_CONNECTION_FAILED"
    DISK_SPACE_CRITICAL = "DISK_SPACE_CRITICAL"
    MEMORY_USAGE_CRITICAL = "MEMORY_USAGE_CRITICAL"
    SYSTEM_MAINTENANCE_MODE = "SYSTEM_MAINTENANCE_MODE"
    XML_VALIDATION_FAILED = "XML_VALIDATION_FAILED"
    
    # --- CATEGORY 2: VALIDATION ERRORS (400) ---
    LEDGER_NOT_FOUND = "LEDGER_NOT_FOUND"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INVALID_DATE = "INVALID_DATE"
    INVALID_GST_RATE = "INVALID_GST_RATE"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    MESSAGE_TOO_LONG = "MESSAGE_TOO_LONG"
    MESSAGE_TOO_SHORT = "MESSAGE_TOO_SHORT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_VOUCHER_TYPE = "INVALID_VOUCHER_TYPE"
    INVALID_EMAIL_FORMAT = "INVALID_EMAIL_FORMAT"
    INVALID_PHONE_FORMAT = "INVALID_PHONE_FORMAT"
    INVALID_PAN_FORMAT = "INVALID_PAN_FORMAT"
    INVALID_GSTIN_FORMAT = "INVALID_GSTIN_FORMAT"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    
    # --- CATEGORY 3: FINANCIAL COMPLIANCE (409/400) ---
    DUPLICATE_INVOICE_DETECTED = "DUPLICATE_INVOICE_DETECTED"
    CREDIT_LIMIT_EXCEEDED = "CREDIT_LIMIT_EXCEEDED"
    REVERSE_CHARGE_APPLICABLE = "REVERSE_CHARGE_APPLICABLE"
    TDS_OBLIGATION = "TDS_OBLIGATION"
    GSTIN_MISMATCH = "GSTIN_MISMATCH"
    E_INVOICE_REQUIRED = "E_INVOICE_REQUIRED"
    E_WAY_BILL_REQUIRED = "E_WAY_BILL_REQUIRED"
    HSN_CODE_MISMATCH = "HSN_CODE_MISMATCH"
    PARTY_GSTIN_INACTIVE = "PARTY_GSTIN_INACTIVE"
    PLACE_OF_SUPPLY_MISMATCH = "PLACE_OF_SUPPLY_MISMATCH"
    NEGATIVE_STOCK_WARNING = "NEGATIVE_STOCK_WARNING"
    FINANCIAL_YEAR_LOCKED = "FINANCIAL_YEAR_LOCKED"
    
    # --- CATEGORY 4: TALLY SPECIFIC ERRORS ---
    TALLY_XML_PARSE_ERROR = "TALLY_XML_PARSE_ERROR"
    TALLY_SYNC_FAILED = "TALLY_SYNC_FAILED"
    TALLY_COMPANY_NOT_OPEN = "TALLY_COMPANY_NOT_OPEN"
    TALLY_EDU_MODE_RESTRICTION = "TALLY_EDU_MODE_RESTRICTION"
    TALLY_ACCESS_DENIED = "TALLY_ACCESS_DENIED"
    TALLY_LICENSE_EXPIRED = "TALLY_LICENSE_EXPIRED"
    TALLY_VERSION_MISMATCH = "TALLY_VERSION_MISMATCH"
    
    # --- CATEGORY 5: WORKFLOW & LOGIC ---
    WORKFLOW_STEP_FAILED = "WORKFLOW_STEP_FAILED"
    STATE_TRANSITION_INVALID = "STATE_TRANSITION_INVALID"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    FEATURE_DISABLED = "FEATURE_DISABLED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # --- CATEGORY 6: SECURITY ---
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    INVALID_API_KEY = "INVALID_API_KEY"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SUSPICIOUS_ACTIVITY_DETECTED = "SUSPICIOUS_ACTIVITY_DETECTED"
    
    # --- FALLBACK ---
    UNKNOWN_ERROR = "UNKNOWN_ERROR"



@dataclass
class AgentError:
    """Structured error object for agent operations"""
    code: K24ErrorCode
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    suggestions: List[str]
    retry_available: bool
    retry_count: int = 0
    max_retries: int = 2
    timestamp: str = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if self.context is None:
            self.context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API responses"""
        return {
            "status": "FAILED",
            "error_code": self.code.value,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestions": self.suggestions,
            "retry_available": self.retry_available,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timestamp": self.timestamp,
            "context": self.context
        }


# Error Configuration Map
ERROR_CONFIG: Dict[K24ErrorCode, Dict[str, Any]] = {
    # System
    K24ErrorCode.DATABASE_CONNECTION_FAILED: {"severity": ErrorSeverity.CRITICAL, "category": ErrorCategory.SYSTEM, "retry_available": True, "max_retries": 3},
    K24ErrorCode.TALLY_CONNECTION_FAILED: {"severity": ErrorSeverity.CRITICAL, "category": ErrorCategory.TALLY_CONNECTION, "retry_available": True, "max_retries": 2},
    K24ErrorCode.GEMINI_API_TIMEOUT: {"severity": ErrorSeverity.HIGH, "category": ErrorCategory.GEMINI_API, "retry_available": True, "max_retries": 3},
    K24ErrorCode.GEMINI_API_RATE_LIMIT: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.GEMINI_API, "retry_available": True, "max_retries": 5},
    K24ErrorCode.GEMINI_API_AUTH_FAILED: {"severity": ErrorSeverity.CRITICAL, "category": ErrorCategory.GEMINI_API, "retry_available": False, "max_retries": 0},
    K24ErrorCode.REDIS_CONNECTION_FAILED: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.SYSTEM, "retry_available": True, "max_retries": 1},
    
    # Validation
    K24ErrorCode.LEDGER_NOT_FOUND: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.VALIDATION, "retry_available": True, "max_retries": 1},
    K24ErrorCode.INVALID_AMOUNT: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.VALIDATION, "retry_available": True, "max_retries": 2},
    K24ErrorCode.INVALID_DATE: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.VALIDATION, "retry_available": True, "max_retries": 2},
    K24ErrorCode.INVALID_GST_RATE: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.VALIDATION, "retry_available": True, "max_retries": 2},
    K24ErrorCode.MALFORMED_REQUEST: {"severity": ErrorSeverity.LOW, "category": ErrorCategory.VALIDATION, "retry_available": False, "max_retries": 0},
    K24ErrorCode.MESSAGE_TOO_LONG: {"severity": ErrorSeverity.LOW, "category": ErrorCategory.VALIDATION, "retry_available": False, "max_retries": 0},
    K24ErrorCode.MESSAGE_TOO_SHORT: {"severity": ErrorSeverity.LOW, "category": ErrorCategory.VALIDATION, "retry_available": False, "max_retries": 0},
    K24ErrorCode.INVALID_GSTIN_FORMAT: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.VALIDATION, "retry_available": True, "max_retries": 1},
    
    # Financial
    K24ErrorCode.DUPLICATE_INVOICE_DETECTED: {"severity": ErrorSeverity.HIGH, "category": ErrorCategory.FINANCIAL, "retry_available": False, "max_retries": 0},
    K24ErrorCode.CREDIT_LIMIT_EXCEEDED: {"severity": ErrorSeverity.HIGH, "category": ErrorCategory.FINANCIAL, "retry_available": False, "max_retries": 0},
    K24ErrorCode.REVERSE_CHARGE_APPLICABLE: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.FINANCIAL, "retry_available": False, "max_retries": 0},
    K24ErrorCode.TDS_OBLIGATION: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.FINANCIAL, "retry_available": False, "max_retries": 0},
    K24ErrorCode.GSTIN_MISMATCH: {"severity": ErrorSeverity.HIGH, "category": ErrorCategory.FINANCIAL, "retry_available": False, "max_retries": 0},
    K24ErrorCode.NEGATIVE_STOCK_WARNING: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.FINANCIAL, "retry_available": False, "max_retries": 0},
    
    # Tally
    K24ErrorCode.TALLY_COMPANY_NOT_OPEN: {"severity": ErrorSeverity.HIGH, "category": ErrorCategory.TALLY_CONNECTION, "retry_available": True, "max_retries": 1},
    K24ErrorCode.TALLY_EDU_MODE_RESTRICTION: {"severity": ErrorSeverity.MEDIUM, "category": ErrorCategory.TALLY_CONNECTION, "retry_available": False, "max_retries": 0},
    
    # Security
    K24ErrorCode.UNAUTHORIZED_ACCESS: {"severity": ErrorSeverity.CRITICAL, "category": ErrorCategory.SYSTEM, "retry_available": False, "max_retries": 0},
    K24ErrorCode.INVALID_API_KEY: {"severity": ErrorSeverity.CRITICAL, "category": ErrorCategory.SYSTEM, "retry_available": False, "max_retries": 0},
}


def create_error(
    error_code: K24ErrorCode,
    message: str = None,
    suggestions: List[str] = None,
    context: Dict[str, Any] = None,
    retry_count: int = 0
) -> AgentError:
    """Factory function to create standardized errors"""
    
    config = ERROR_CONFIG.get(error_code, {
        "severity": ErrorSeverity.MEDIUM,
        "category": ErrorCategory.SYSTEM,
        "retry_available": False,
        "max_retries": 0,
        "default_message": "An error occurred"
    })
    
    return AgentError(
        code=error_code,
        severity=config["severity"],
        category=config["category"],
        message=message or config["default_message"],
        suggestions=suggestions or [],
        retry_available=config["retry_available"],
        retry_count=retry_count,
        max_retries=config["max_retries"],
        context=context or {}
    )
