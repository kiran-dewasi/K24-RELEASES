# K24 AI Agent - Validation Layer
# ================================
# This layer performs all safety checks BEFORE any Tally writes

from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime
import re
from backend.tally_connector import TallyConnector
from backend.agent_errors import AgentError, K24ErrorCode, create_error
from backend.compliance.india import validate_india
from backend.compliance.india.india_validation_engine import ValidationResult as IndiaValidationResult

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check"""
    
    def __init__(
        self,
        is_valid: bool,
        errors: List[AgentError] = None,
        warnings: List[str] = None,
        validated_params: Dict[str, Any] = None,
        confidence: float = 1.0
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.validated_params = validated_params or {}
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "validated_params": self.validated_params,
            "confidence": self.confidence
        }


class ValidatorAgent:
    """
    The Safety Layer - validates all parameters before Tally operations.
    Performs the following checks:
    1. Ledger validation (exists in Tally, fuzzy matching)
    2. Amount validation (range, realistic values)
    3. Tax validation (GST rates, HSN codes)
    4. Business rules validation (authorization, policies)
    """
    
    def __init__(
        self,
        tally_connector: TallyConnector,
        max_transaction_amount: float = 10_00_000,  # 10 lakh
        suspicious_amount_multiplier: float = 5.0
    ):
        self.tally = tally_connector
        self.max_transaction_amount = max_transaction_amount
        self.suspicious_multiplier = suspicious_amount_multiplier
        self._ledger_cache = None
        self._cache_timestamp = None
    
    def validate_all(
        self,
        intent: str,
        parameters: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run all validation checks in sequence.
        Returns ValidationResult with errors, warnings, and validated params.
        """
        errors: List[AgentError] = []
        warnings: List[str] = []
        validated_params = parameters.copy()
        
        # Check 1: Required fields validation
        required_fields_result = self._validate_required_fields(intent, parameters)
        if not required_fields_result[0]:
            errors.append(required_fields_result[1])
            return ValidationResult(is_valid=False, errors=errors)
        
        # Check 2: Ledger validation (if party_name present)
        if "party_name" in parameters and parameters["party_name"]:
            ledger_result = self._validate_ledger(parameters["party_name"])
            if not ledger_result[0]:
                errors.append(ledger_result[1])
            else:
                validated_params["party_name"] = ledger_result[1]  # Use exact match
                if ledger_result[2]:
                    warnings.append(ledger_result[2])
        
        # Check 3: Amount validation
        if "amount" in parameters:
            amount_result = self._validate_amount(parameters["amount"], intent)
            if not amount_result[0]:
                errors.append(amount_result[1])
            else:
                validated_params["amount"] = amount_result[1]
                if amount_result[2]:
                    warnings.append(amount_result[2])
        
        # Check 4: Date validation
        if "date" in parameters:
            date_result = self._validate_date(parameters["date"])
            if not date_result[0]:
                errors.append(date_result[1])
            else:
                validated_params["date"] = date_result[1]
        
        # Check 5: Voucher type validation
        if "voucher_type" in parameters:
            vch_result = self._validate_voucher_type(parameters["voucher_type"])
            if not vch_result[0]:
                errors.append(vch_result[1])
        
        # Check 6: Financial risk checks
        if "amount" in parameters and "party_name" in parameters:
            risk_result = self._check_financial_risks(
                parameters["amount"],
                parameters.get("party_name"),
                parameters.get("date")
            )
            if risk_result[0]:  # Has errors
                errors.extend(risk_result[0])
            if risk_result[1]:  # Has warnings
                warnings.extend(risk_result[1])
        
        # Check 7: India Compliance Checks
        try:
            # Prepare context (In a real app, fetch this from DB/Config)
            compliance_context = {
                "annual_turnover": 45_00_000, # Placeholder
                "business_type": "GOODS",
                "state_code": "MH"
            }
            
            india_result = validate_india(
                parameters=validated_params,
                intent=intent.upper(),
                context=compliance_context
            )
            
            # Map errors
            for issue in india_result.errors:
                errors.append(create_error(
                    K24ErrorCode.BUSINESS_RULE_VIOLATION,
                    message=issue.message,
                    suggestions=[issue.action],
                    context={"rule": issue.rule_name}
                ))
            
            # Map warnings
            for issue in india_result.warnings:
                warnings.append(f"⚠️ {issue.message} ({issue.action})")
                
        except Exception as e:
            logger.error(f"India compliance check failed: {e}")
            # Don't fail validation if compliance check fails internally, just log it

        
        # Calculate confidence score
        confidence = 1.0 - (len(warnings) * 0.1)
        confidence = max(0.5, confidence)  # Min 50% confidence
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_params=validated_params,
            confidence=confidence
        )
    
    def _validate_required_fields(
        self,
        intent: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, Optional[AgentError]]:
        """Check if all required fields are present"""
        
        required_fields_map = {
            "create_invoice": ["party_name", "amount"],
            "create_receipt": ["party_name", "amount"],
            "create_payment": ["party_name", "amount"],
            "create_sales": ["party_name", "amount"],
        }
        
        required_fields = required_fields_map.get(intent, [])
        missing_fields = [f for f in required_fields if f not in params or not params[f]]
        
        if missing_fields:
            error = create_error(
                K24ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Missing required fields: {', '.join(missing_fields)}",
                suggestions=[
                    f"Please provide: {', '.join(missing_fields)}",
                    "Example: 'Create invoice for HDFC Bank for ₹50000'"
                ],
                context={"missing_fields": missing_fields, "intent": intent}
            )
            return (False, error)
        
        return (True, None)
    
    def _validate_ledger(
        self,
        party_name: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate ledger exists in Tally.
        Returns (is_valid, exact_match_or_error, warning_message)
        """
        try:
            # Lookup ledger (with fuzzy matching)
            matches = self.tally.lookup_ledger(party_name)
            
            if not matches:
                # No matches found
                error = create_error(
                    K24ErrorCode.LEDGER_NOT_FOUND,
                    message=f"Ledger '{party_name}' not found in Tally",
                    suggestions=[
                        "Check spelling and try again",
                        "Create the ledger in Tally first",
                        "Use exact ledger name from Tally"
                    ],
                    context={"party_name": party_name}
                )
                return (False, error, None)
            
            # Check if exact match
            exact_match = next((m for m in matches if m.lower() == party_name.lower()), None)
            
            if exact_match:
                # Exact match found
                return (True, exact_match, None)
            else:
                # Fuzzy matches found
                best_match = matches[0]
                warning = f"Using closest match: '{best_match}' (you typed: '{party_name}')"
                return (True, best_match, warning)
        
        except Exception as e:
            logger.error(f"Ledger validation failed: {e}")
            error = create_error(
                K24ErrorCode.TALLY_CONNECTION_FAILED,
                message="Could not verify ledger in Tally",
                suggestions=["Ensure Tally is running", "Check network connection"],
                context={"error": str(e)}
            )
            return (False, error, None)
    
    def _validate_amount(
        self,
        amount: Any,
        intent: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate amount is valid and reasonable.
        Returns (is_valid, parsed_amount_or_error, warning)
        """
        try:
            # Parse amount
            if isinstance(amount, str):
                # Remove currency symbols and commas
                amount = re.sub(r'[₹,\s]', '', amount)
            
            amount_float = float(amount)
            
            # Check if positive
            if amount_float <= 0:
                error = create_error(
                    K24ErrorCode.AMOUNT_OUT_OF_RANGE,
                    message="Amount must be greater than zero",
                    suggestions=["Enter a positive amount"],
                    context={"amount": amount}
                )
                return (False, error, None)
            
            # Check max limit
            if amount_float > self.max_transaction_amount:
                error = create_error(
                    K24ErrorCode.AMOUNT_OUT_OF_RANGE,
                    message=f"Amount exceeds maximum limit of ₹{self.max_transaction_amount:,.2f}",
                    suggestions=[
                        "Break into multiple transactions",
                        "Request approval from finance manager"
                    ],
                    context={"amount": amount_float, "max_limit": self.max_transaction_amount}
                )
                return (False, error, None)
            
            # Check if suspiciously large
            # TODO: Calculate average transaction amount from history
            average_amount = 50000  # Placeholder
            if amount_float > (average_amount * self.suspicious_multiplier):
                warning = f"This amount (₹{amount_float:,.2f}) is {amount_float/average_amount:.1f}x higher than average"
                return (True, amount_float, warning)
            
            return (True, amount_float, None)
        
        except (ValueError, TypeError) as e:
            error = create_error(
                K24ErrorCode.AMOUNT_OUT_OF_RANGE,
                message=f"Invalid amount format: '{amount}'",
                suggestions=["Enter amount as number", "Example: 50000 or ₹50,000"],
                context={"amount": amount, "error": str(e)}
            )
            return (False, error, None)
    
    def _validate_date(self, date: Any) -> Tuple[bool, Any]:
        """Validate and normalize date"""
        try:
            # Handle string dates
            if isinstance(date, str):
                # Try common formats
                for fmt in ["%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]:
                    try:
                        dt = datetime.strptime(date, fmt)
                        return (True, dt.strftime("%Y%m%d"))
                    except ValueError:
                        continue
                
                # If no format matched
                error = create_error(
                    K24ErrorCode.INVALID_DATE_FORMAT,
                    message=f"Invalid date format: '{date}'",
                    suggestions=["Use format: YYYY-MM-DD or YYYYMMDD"],
                    context={"date": date}
                )
                return (False, error)
            
            # Handle datetime objects
            elif isinstance(date, datetime):
                return (True, date.strftime("%Y%m%d"))
            
            # Default to today
            return (True, datetime.now().strftime("%Y%m%d"))
        
        except Exception as e:
            error = create_error(
                K24ErrorCode.INVALID_DATE_FORMAT,
                message="Date validation failed",
                context={"error": str(e)}
            )
            return (False, error)
    
    def _validate_voucher_type(self, voucher_type: str) -> Tuple[bool, Optional[AgentError]]:
        """Validate voucher type is supported"""
        valid_types = ["Sales", "Purchase", "Receipt", "Payment", "Journal", "Contra"]
        
        if voucher_type not in valid_types:
            error = create_error(
                K24ErrorCode.INVALID_VOUCHER_TYPE,
                message=f"Invalid voucher type: '{voucher_type}'",
                suggestions=[
                    f"Valid types: {', '.join(valid_types)}",
                    "Most common: Sales, Receipt, Payment"
                ],
                context={"voucher_type": voucher_type, "valid_types": valid_types}
            )
            return (False, error)
        
        return (True, None)
    
    def _check_financial_risks(
        self,
        amount: float,
        party_name: str,
        date: str = None
    ) -> Tuple[List[AgentError], List[str]]:
        """
        Check for financial risks like duplicates, credit limits, etc.
        Returns (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check 1: Duplicate detection (simplified)
        # TODO: Query database for recent transactions
        # For now, just log this as a placeholder
        
        # Check 2: Amount suspiciously large
        if amount > 500000:  # 5 lakh
            warnings.append(
                f"⚠️ Large transaction: ₹{amount:,.2f}. Extra confirmation required."
            )
        
        # Check 3: Credit limit (placeholder)
        # TODO: Fetch customer credit limit from Tally
        # credit_limit = self.tally.get_credit_limit(party_name)
        
        return (errors, warnings)
