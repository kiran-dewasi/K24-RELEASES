"""
K24 Indian Compliance Package
==============================
India-specific tax and compliance validation for SMBs.
"""

from backend.compliance.india.india_validation_rules import *
from backend.compliance.india.india_validation_engine import (
    ValidationResult,
    ValidationIssue,
    IndiaValidationEngine,
    validate_india
)
from backend.compliance.india.india_tax_calculator import (
    IndiaTaxCalculator,
    calculate_gst,
    calculate_tds,
    calculate_rcm
)
from backend.compliance.india.india_compliance_calendar import (
    IndiaComplianceCalendar,
    get_upcoming_deadlines,
    is_near_deadline
)

__all__ = [
    "ValidationResult",
    "ValidationIssue",
    "IndiaValidationEngine",
    "validate_india",
    "IndiaTaxCalculator",
    "calculate_gst",
    "calculate_tds",
    "calculate_rcm",
    "IndiaComplianceCalendar",
    "get_upcoming_deadlines",
    "is_near_deadline",
]
