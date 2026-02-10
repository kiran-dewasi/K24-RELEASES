# K24 AI Agent - Error Handler with Retry Logic
# ===============================================
# Implements exponential backoff, retry policies, and fallback strategies

from typing import Dict, Any, Callable, Optional, TypeVar, List
import logging
import time
import functools
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    RetryError
)
from backend.agent_errors import (
    AgentError,
    K24ErrorCode,
    ErrorSeverity,
    ErrorCategory,
    create_error
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""
    
    # Retry policies by error code
    POLICIES = {
        K24ErrorCode.GEMINI_API_TIMEOUT: {
            "max_attempts": 3,
            "wait_strategy": "exponential",
            "wait_multiplier": 1,
            "wait_max": 10,
            "fallback": "use_template"
        },
        K24ErrorCode.GEMINI_API_ERROR: {
            "max_attempts": 2,
            "wait_strategy": "exponential",
            "wait_multiplier": 2,
            "wait_max": 8,
            "fallback": "use_template"
        },
        K24ErrorCode.GEMINI_API_RATE_LIMIT: {
            "max_attempts": 5,
            "wait_strategy": "exponential",
            "wait_multiplier": 2,
            "wait_max": 30,
            "fallback": "queue_for_later"
        },
        K24ErrorCode.TALLY_CONNECTION_FAILED: {
            "max_attempts": 3,
            "wait_strategy": "fixed",
            "wait_seconds": 5,
            "fallback": "queue_for_later"
        },
        K24ErrorCode.DATABASE_CONNECTION_FAILED: {
            "max_attempts": 3,
            "wait_strategy": "fixed",
            "wait_seconds": 2,
            "fallback": "read_only_mode"
        },
        K24ErrorCode.XML_VALIDATION_FAILED: {
            "max_attempts": 2,
            "wait_strategy": "none",
            "fallback": "manual_form"
        },
        K24ErrorCode.LEDGER_NOT_FOUND: {
            "max_attempts": 1,
            "wait_strategy": "none",
            "fallback": "suggest_alternatives"
        },
        K24ErrorCode.INVALID_AMOUNT: {
            "max_attempts": 1,
            "wait_strategy": "none",
            "fallback": "ask_correction"
        },
    }
    
    @classmethod
    def get_policy(cls, error_code: K24ErrorCode) -> Dict[str, Any]:
        """Get retry policy for error code"""
        return cls.POLICIES.get(error_code, {
            "max_attempts": 1,
            "wait_strategy": "none",
            "fallback": None
        })


class AgentErrorHandler:
    """
    Centralized error handling with retry logic and fallbacks.
    Tracks retry attempts and provides structured error responses.
    """
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
    
    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        retry_count: int = 0
    ) -> AgentError:
        """
        Handle an error and convert to AgentError.
        Determines if retry is possible.
        """
        context = context or {}
        
        # Classify the error
        error_code = self._classify_error(error)
        
        # Get retry policy
        policy = RetryConfig.get_policy(error_code)
        max_retries = policy.get("max_attempts", 1) - 1  # -1 because first attempt doesn't count
        
        # Determine if retryable
        is_retryable = retry_count < max_retries
        
        # Get suggestions
        suggestions = self._get_error_suggestions(error_code, context)
        
        # Create structured error
        agent_error = create_error(
            error_code=error_code,
            message=str(error),
            suggestions=suggestions,
            context=context,
            retry_count=retry_count
        )
        
        # Log error
        logger.error(
            f"Error handled: {error_code.value} (retry {retry_count}/{max_retries})",
            extra={"error_details": agent_error.to_dict()}
        )
        
        return agent_error
    
    def _classify_error(self, error: Exception) -> K24ErrorCode:
        """Classify exception into K24ErrorCode"""
        
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # --- SYSTEM ERRORS ---
        if "timeout" in error_message or "timed out" in error_message:
            return K24ErrorCode.GEMINI_API_TIMEOUT
            
        if "rate limit" in error_message or "429" in error_message:
            return K24ErrorCode.GEMINI_API_RATE_LIMIT
            
        if any(word in error_message for word in ["auth", "permission", "401", "403", "key"]):
            if "gemini" in error_message or "api" in error_message:
                return K24ErrorCode.GEMINI_API_AUTH_FAILED
            return K24ErrorCode.UNAUTHORIZED_ACCESS
            
        if any(word in error_message for word in ["database", "sqlalchemy", "db connection"]):
            return K24ErrorCode.DATABASE_CONNECTION_FAILED
            
        if "redis" in error_message:
            return K24ErrorCode.REDIS_CONNECTION_FAILED
            
        if any(word in error_message for word in ["tally", "connection", "localhost:9000"]):
            return K24ErrorCode.TALLY_CONNECTION_FAILED
            
        # --- VALIDATION ERRORS ---
        if "ledger" in error_message and "not found" in error_message:
            return K24ErrorCode.LEDGER_NOT_FOUND
            
        if "amount" in error_message:
            if "invalid" in error_message or "negative" in error_message:
                return K24ErrorCode.INVALID_AMOUNT
            if "large" in error_message:
                return K24ErrorCode.AMOUNT_SUSPICIOUSLY_LARGE
                
        if "date" in error_message:
            return K24ErrorCode.INVALID_DATE
            
        if "gst" in error_message and "rate" in error_message:
            return K24ErrorCode.INVALID_GST_RATE
            
        if "gstin" in error_message:
            return K24ErrorCode.INVALID_GSTIN_FORMAT
            
        # --- FINANCIAL ERRORS ---
        if "duplicate" in error_message:
            return K24ErrorCode.DUPLICATE_INVOICE_DETECTED
            
        if "credit limit" in error_message:
            return K24ErrorCode.CREDIT_LIMIT_EXCEEDED
            
        if "reverse charge" in error_message:
            return K24ErrorCode.REVERSE_CHARGE_APPLICABLE
            
        if "tds" in error_message:
            return K24ErrorCode.TDS_OBLIGATION
            
        # --- GENERIC FALLBACKS ---
        if any(word in error_message for word in ["xml", "parse", "malformed"]):
            return K24ErrorCode.XML_VALIDATION_FAILED
            
        if any(word in error_message for word in ["api", "gemini"]):
            return K24ErrorCode.GEMINI_API_ERROR
        
        return K24ErrorCode.UNKNOWN_ERROR
    
    def _get_error_suggestions(self, error_code: K24ErrorCode, context: Dict[str, Any]) -> List[str]:
        """Get actionable suggestions for an error"""
        
        suggestions_map = {
            # --- SYSTEM ---
            K24ErrorCode.DATABASE_CONNECTION_FAILED: [
                "Database is temporarily unavailable. Please wait a moment.",
                "Retry after 60 seconds",
                "Contact support if issue persists"
            ],
            K24ErrorCode.TALLY_CONNECTION_FAILED: [
                "Can't reach your Tally. Check your ODBC connection.",
                "Verify Tally is running on port 9000",
                "Ensure Tally company is open"
            ],
            K24ErrorCode.GEMINI_API_TIMEOUT: [
                "AI agent is thinking too long. Let's try again?",
                "Retrying automatically...",
                "If this persists, try rephrasing your request"
            ],
            K24ErrorCode.GEMINI_API_RATE_LIMIT: [
                "Too many AI requests right now. Wait a moment?",
                "We've queued your request for processing",
                "Try again in 30 seconds"
            ],
            K24ErrorCode.GEMINI_API_AUTH_FAILED: [
                "AI service authentication error. Contact support.",
                "Check API key configuration"
            ],
            K24ErrorCode.REDIS_CONNECTION_FAILED: [
                "Cache service unavailable. System still working.",
                "Performance might be slightly slower"
            ],
            
            # --- VALIDATION ---
            K24ErrorCode.LEDGER_NOT_FOUND: [
                f"Ledger '{context.get('party_name', 'Unknown')}' not found in your Tally.",
                "Did you mean one of these?",
                "Select from suggestions or create new ledger?"
            ],
            K24ErrorCode.INVALID_AMOUNT: [
                f"Amount must be between ₹0 and ₹{context.get('max_limit', '1,00,00,000')}.",
                "Edit amount and try again.",
                f"You entered: {context.get('amount', 'Unknown')}"
            ],
            K24ErrorCode.INVALID_DATE: [
                "Date must be between [90 days ago] and [today].",
                "Select valid date and try again.",
                f"You entered: {context.get('date', 'Unknown')}"
            ],
            K24ErrorCode.INVALID_GST_RATE: [
                "GST rate must be one of: 0%, 5%, 12%, 18%, 28%",
                "For this item type, rate should likely be 18%",
                "Use suggested rate?"
            ],
            K24ErrorCode.MALFORMED_REQUEST: [
                "Your message format is unclear.",
                "Try: 'Create invoice for ABC Corp ₹50,000 with 18% GST'",
                "Rephrase and try again"
            ],
            K24ErrorCode.MESSAGE_TOO_LONG: [
                "Message is too long (>2000 characters).",
                "Break into shorter messages"
            ],
            K24ErrorCode.MESSAGE_TOO_SHORT: [
                "Message too short. Please be more specific.",
                "Add more details"
            ],
            
            # --- FINANCIAL ---
            K24ErrorCode.DUPLICATE_INVOICE_DETECTED: [
                "This looks like a duplicate invoice.",
                f"Similar exists: {context.get('duplicate_details', 'Check recent entries')}",
                "Proceed anyway? [Yes/No]"
            ],
            K24ErrorCode.CREDIT_LIMIT_EXCEEDED: [
                "Customer credit limit exceeded.",
                f"Limit: ₹{context.get('credit_limit', 'Unknown')} | Outstanding: ₹{context.get('outstanding', 'Unknown')}",
                "Request approval from Finance Manager"
            ],
            K24ErrorCode.REVERSE_CHARGE_APPLICABLE: [
                "Reverse Charge applies to this purchase.",
                "You must pay GST under RCM",
                "Confirm to proceed with RCM"
            ],
            K24ErrorCode.TDS_OBLIGATION: [
                "TDS deduction required.",
                f"Deduct TDS under Section {context.get('tds_section', '194C')}",
                "Automatic deduction, confirm? [Yes/No]"
            ],
            K24ErrorCode.GSTIN_MISMATCH: [
                "GSTIN doesn't match the state code",
                "Verify GSTIN and State",
                "Update party master?"
            ],
            
            # --- TALLY ---
            K24ErrorCode.TALLY_COMPANY_NOT_OPEN: [
                "No company is open in Tally",
                "Please open a company in Tally Prime",
                "Check Tally status"
            ],
            K24ErrorCode.TALLY_EDU_MODE_RESTRICTION: [
                "Tally is in Educational Mode",
                "Dates are restricted to 1st, 2nd, and 31st",
                "Change date to 1st or 2nd?"
            ]
        }
        
        return suggestions_map.get(error_code, ["Please try again or contact support"])
    
    def with_retry(
        self,
        func: Callable[..., T],
        error_code: K24ErrorCode,
        context: Dict[str, Any] = None
    ) -> Callable[..., T]:
        """
        Decorator factory to add retry logic to a function.
        """
        policy = RetryConfig.get_policy(error_code)
        max_attempts = policy.get("max_attempts", 1)
        wait_strategy = policy.get("wait_strategy", "none")
        
        # Build retry decorator
        retry_kwargs = {
            "stop": stop_after_attempt(max_attempts),
            "reraise": True
        }
        
        if wait_strategy == "exponential":
            retry_kwargs["wait"] = wait_exponential(
                multiplier=policy.get("wait_multiplier", 1),
                max=policy.get("wait_max", 10)
            )
        elif wait_strategy == "fixed":
            retry_kwargs["wait"] = wait_fixed(policy.get("wait_seconds", 2))
        
        retry_decorator = retry(**retry_kwargs)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                # All retries exhausted
                logger.error(f"All retries exhausted for {func.__name__}")
                raise e.last_attempt.exception()
        
        return wrapper


class FallbackStrategies:
    """
    Fallback strategies when primary methods fail.
    """
    
    @staticmethod
    def use_template_xml(voucher_type: str, params: Dict[str, Any]) -> str:
        """
        Generate XML using template when Gemini fails.
        Simple but reliable fallback.
        """
        from backend.tally_xml_builder import build_voucher_xml
        
        logger.info("Using template-based XML generation as fallback")
        
        try:
            # Use existing XML builder
            xml = build_voucher_xml(
                voucher_type=voucher_type,
                party_name=params.get("party_name"),
                amount=params.get("amount"),
                date=params.get("date"),
                narration=params.get("narration", ""),
                company_name=params.get("company_name")
            )
            return xml
        except Exception as e:
            logger.error(f"Template XML generation also failed: {e}")
            raise
    
    @staticmethod
    def queue_for_later(transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Queue transaction for later processing when Tally is unavailable.
        """
        logger.info("Queueing transaction for later processing")
        
        # TODO: Implement actual queue (Redis, database, etc.)
        # For now, just return a pending status
        
        return {
            "status": "QUEUED",
            "message": "Tally is currently unavailable. Transaction will be processed when connection is restored.",
            "transaction_id": transaction_data.get("transaction_id"),
            "queued_at": datetime.utcnow().isoformat() + "Z"
        }
    
    @staticmethod
    def suggest_alternatives(query: str, available_options: List[str]) -> Dict[str, Any]:
        """
        Suggest alternatives when exact match not found.
        Uses fuzzy matching.
        """
        from difflib import get_close_matches
        
        # Find close matches
        matches = get_close_matches(query, available_options, n=5, cutoff=0.6)
        
        return {
            "status": "NEEDS_CLARIFICATION",
            "message": f"'{query}' not found",
            "suggestions": matches,
            "action_required": "select_from_suggestions"
        }
    
    @staticmethod
    def manual_form_fallback(intent: str, partial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return data structure for manual form entry.
        """
        return {
            "status": "MANUAL_ENTRY_REQUIRED",
            "message": "Automatic processing failed. Please use manual entry form.",
            "intent": intent,
            "pre_filled_data": partial_data,
            "form_url": f"/vouchers/new/{intent.replace('create_', '')}"
        }


def retry_with_backoff(
    error_code: K24ErrorCode,
    max_attempts: int = None
):
    """
    Decorator to add retry logic with backoff to any function.
    
    Usage:
        @retry_with_backoff(K24ErrorCode.GEMINI_API_TIMEOUT)
        def my_function():
            # ... code that might fail
    """
    policy = RetryConfig.get_policy(error_code)
    attempts = max_attempts or policy.get("max_attempts", 3)
    wait_strategy = policy.get("wait_strategy", "exponential")
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts - 1:
                        # Last attempt failed
                        logger.error(f"{func.__name__} failed after {attempts} attempts: {e}")
                        raise
                    
                    # Calculate wait time
                    if wait_strategy == "exponential":
                        wait_time = min(2 ** attempt, policy.get("wait_max", 10))
                    elif wait_strategy == "fixed":
                        wait_time = policy.get("wait_seconds", 2)
                    else:
                        wait_time = 0
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{attempts} failed. "
                        f"Retrying in {wait_time}s... Error: {e}"
                    )
                    
                    if wait_time > 0:
                        time.sleep(wait_time)
        
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    handler = AgentErrorHandler()
    
    # Simulate handling different errors
    test_errors = [
        (Exception("Gemini API timeout"), {"operation": "xml_generation"}),
        (Exception("Tally connection refused"), {"tally_url": "localhost:9000"}),
        (Exception("Ledger 'ABC Corp' not found"), {"party_name": "ABC Corp"}),
    ]
    
    for error, context in test_errors:
        agent_error = handler.handle_error(error, context, retry_count=0)
        print(f"\nError: {error}")
        print(f"Classified as: {agent_error.code.value}")
        print(f"Suggestions: {agent_error.suggestions}")
        print(f"Retryable: {agent_error.retry_available}")
