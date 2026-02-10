"""
K24 Parameter Extraction - Validator
=====================================
Validate parameters against business rules and Tally database.
"""

import logging
from typing import Tuple, Optional, Dict, Any
from backend.database import SessionLocal, Ledger, Voucher

logger = logging.getLogger(__name__)

class ParameterValidator:
    """Validates extracted parameters against business rules"""
    
    @staticmethod
    def validate_ledger_exists(ledger_name: str) -> Tuple[bool, Optional[str]]:
        """Check if ledger exists in Tally"""
        db = SessionLocal()
        try:
            ledger = db.query(Ledger).filter(
                Ledger.name == ledger_name,
                Ledger.is_active == True
            ).first()
            
            if ledger:
                return True, None
            else:
                return False, f"Ledger '{ledger_name}' not found"
        except Exception as e:
            logger.error(f"Ledger validation error: {e}")
            return False, f"Database error: {str(e)}"
        finally:
            db.close()
    
    @staticmethod
    def validate_amount_range(amount: float, min_val: float = 0, max_val: float = 10_000_000) -> Tuple[bool, Optional[str]]:
        """Validate amount is within acceptable range"""
        if amount <= min_val:
            return False, f"Amount must be greater than ₹{min_val:,.0f}"
        if amount > max_val:
            return False, f"Amount exceeds maximum of ₹{max_val:,.0f}"
        return True, None
    
    @staticmethod
    def validate_gst_rate(rate: float) -> Tuple[bool, Optional[str]]:
        """Validate GST rate is valid Indian slab"""
        valid_slabs = [0.0, 5.0, 12.0, 18.0, 28.0]
        if rate not in valid_slabs:
            valid_str = ', '.join([f'{r}%' for r in valid_slabs])
            return False, f"Invalid GST rate. Must be one of: {valid_str}"
        return True, None
    
    @staticmethod
    def validate_reference_unique(ref_number: str) -> Tuple[bool, Optional[str]]:
        """Check if reference number is unique"""
        db = SessionLocal()
        try:
            voucher = db.query(Voucher).filter(
                Voucher.voucher_number == ref_number
            ).first()
            
            if voucher:
                return False, f"Reference number '{ref_number}' already exists"
            return True, None
        except Exception as e:
            logger.error(f"Reference validation error: {e}")
            return True, None  # Allow on error
        finally:
            db.close()

def validate_parameter(param_name: str, value: Any, context: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a single parameter.
    
    Args:
        param_name: Parameter name (e.g., "amount", "customer_name")
        value: Parameter value
        context: Additional context for validation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = ParameterValidator()
    
    if param_name == "customer_name":
        return validator.validate_ledger_exists(value)
    elif param_name == "amount":
        return validator.validate_amount_range(value)
    elif param_name == "gst_rate":
        return validator.validate_gst_rate(value)
    elif param_name == "reference_number":
        return validator.validate_reference_unique(value)
    else:
        return True, None
