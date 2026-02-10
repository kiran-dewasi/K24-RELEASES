from typing import Dict, Any

class TallyErrorDecoder:
    """Decode Tally XML error responses"""

    ERROR_PATTERNS = {
        "Ledger already exists": {
            "cause": "Duplicate ledger creation",
            "solution": "Use ACTION='Alter' instead of 'Create' for existing ledgers",
            "prevention": "Query existing ledgers before creating"
        },
        "Parent not found": {
            "cause": "Parent group doesn't exist or typo",
            "solution": "Check parent name spelling: 'Sundry Debtors' or 'Sundry Creditors'",
            "prevention": "Validate parent exists in Tally first"
        },
        "Invalid GST format": {
            "cause": "GSTIN not 15 chars or wrong format",
            "solution": "GSTIN must be: AABBBBBBBBBBBB (15 chars, state code + GSTIN body)",
            "prevention": "Validate GSTIN length and format before sending"
        },
        "Debits != Credits": {
            "cause": "Voucher line items don't balance",
            "solution": "Calculate total debits and credits in Python, must be equal",
            "prevention": "Validate balance before building XML"
        },
        "Duplicate voucher number": {
            "cause": "Same voucher number posted twice",
            "solution": "Use Tally's auto-numbering (don't set voucher number)",
            "prevention": "Let Tally auto-number, store result in Supabase"
        },
        "Date out of fiscal year": {
            "cause": "Voucher date outside company FY",
            "solution": "Use date within company fiscal year (typically Apr-Mar)",
            "prevention": "Query company FY dates, validate date range"
        }
    }

    @staticmethod
    def decode_error(tally_error_msg: str) -> Dict[str, str]:
        """Match error message to patterns and return solution"""
        for pattern, solution in TallyErrorDecoder.ERROR_PATTERNS.items():
            if pattern.lower() in tally_error_msg.lower():
                return solution
        return {
            "cause": "Unknown Tally error",
            "solution": "Check Tally.IMP log file at Tally installation directory",
            "prevention": "Enable detailed logging in Tally"
        }
