"""
K24 Parameter Extraction - Data Models
=======================================
Pydantic models for parameter validation with business rules.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal

class CustomerName(BaseModel):
    """Customer/Party name with fuzzy matching support"""
    value: str = Field(..., max_length=200, description="Customer name")
    ledger_id: Optional[str] = Field(None, description="Tally ledger ID")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Match confidence")
    alternatives: List[str] = Field(default_factory=list, description="Suggested alternatives")
    
    @field_validator('value')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Customer name cannot be empty')
        if len(v) > 200:
            raise ValueError('Customer name too long (max 200 chars)')
        return v.strip()

class Amount(BaseModel):
    """Financial amount with range and reasonableness validation"""
    value: float = Field(..., gt=0, le=10_000_000, description="Amount in INR")
    currency: str = Field(default="INR", description="Currency code")
    is_reasonable: bool = Field(True, description="Within normal range for customer")
    average_amount: Optional[float] = Field(None, description="Customer's average invoice amount")
    
    @field_validator('value')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > 10_000_000:
            raise ValueError('Amount exceeds maximum limit of ₹10,000,000')
        return round(v, 2)
    
    def check_reasonableness(self, average: Optional[float]) -> tuple[bool, Optional[str]]:
        """Check if amount is reasonable compared to customer average"""
        if not average or average == 0:
            return True, None
        
        if self.value > average * 3:
            warning = f"Amount ₹{self.value:,.0f} is 3x average (₹{average:,.0f}). Confirm?"
            return False, warning
        
        return True, None

class InvoiceDate(BaseModel):
    """Invoice date with business validation"""
    value: date = Field(..., description="Invoice date")
    is_today: bool = Field(False, description="Is today's date")
    is_retroactive: bool = Field(False, description="More than 7 days old")
    days_old: int = Field(0, description="Days from today")
    
    @field_validator('value')
    @classmethod
    def validate_date(cls, v):
        today = date.today()
        
        # Not in future
        if v > today:
            raise ValueError('Invoice date cannot be in the future')
        
        # Not older than 90 days
        ninety_days_ago = today - timedelta(days=90)
        if v < ninety_days_ago:
            raise ValueError(f'Invoice date cannot be older than 90 days (before {ninety_days_ago})')
        
        return v
    
    @classmethod
    def from_string(cls, date_str: str):
        """Parse date from various formats"""
        today = date.today()
        
        # Handle relative dates
        date_str_lower = date_str.lower().strip()
        if date_str_lower in ['today', 'now']:
            return cls(value=today, is_today=True, days_old=0)
        
        if date_str_lower == 'yesterday':
            return cls(value=today - timedelta(days=1), days_old=1)
        
        # Try to parse standard formats
        formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                days_old = (today - parsed_date).days
                is_retroactive = days_old > 7
                return cls(
                    value=parsed_date,
                    is_today=(parsed_date == today),
                    is_retroactive=is_retroactive,
                    days_old=days_old
                )
            except ValueError:
                continue
        
        raise ValueError(f'Could not parse date: {date_str}')

class GstRate(BaseModel):
    """GST rate with validation against valid Indian GST slabs"""
    value: float = Field(..., description="GST percentage")
    is_valid_slab: bool = Field(True, description="Is a valid GST slab")
    suggested_rate: Optional[float] = Field(None, description="Suggested rate based on ledger type")
    
    VALID_SLABS = [0.0, 5.0, 12.0, 18.0, 28.0]
    
    @field_validator('value')
    @classmethod
    def validate_gst_rate(cls, v):
        if v not in cls.VALID_SLABS:
            valid_str = ', '.join([f'{rate}%' for rate in cls.VALID_SLABS])
            raise ValueError(f'Invalid GST rate. Must be one of: {valid_str}')
        return v
    
    @classmethod
    def suggest_for_ledger_type(cls, ledger_type: Optional[str]) -> float:
        """Suggest GST rate based on ledger type"""
        if not ledger_type:
            return 18.0  # Default
        
        ledger_type_upper = ledger_type.upper()
        if 'SERVICE' in ledger_type_upper:
            return 18.0
        elif 'PRODUCT' in ledger_type_upper or 'GOODS' in ledger_type_upper:
            return 12.0
        elif 'EXEMPT' in ledger_type_upper or 'ZERO' in ledger_type_upper:
            return 0.0
        else:
            return 18.0  # Default

class LedgerCode(BaseModel):
    """Tally ledger code/ID"""
    value: str = Field(..., description="Ledger code from Tally")
    ledger_name: str = Field(..., description="Ledger name")
    ledger_type: Optional[str] = Field(None, description="Ledger type (SERVICE/PRODUCT/etc)")
    
    @field_validator('value')
    @classmethod
    def validate_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Ledger code cannot be empty')
        return v.strip()

class Description(BaseModel):
    """Transaction description/narration"""
    value: str = Field(default="Transaction via K24 AI", max_length=500)
    
    @field_validator('value')
    @classmethod
    def validate_description(cls, v):
        # SQL injection prevention (basic)
        dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', '--', '/*', '*/']
        v_upper = v.upper()
        for pattern in dangerous_patterns:
            if pattern in v_upper:
                raise ValueError(f'Description contains invalid pattern: {pattern}')
        
        if len(v) > 500:
            raise ValueError('Description too long (max 500 chars)')
        
        return v.strip()

class ReferenceNumber(BaseModel):
    """Invoice/transaction reference number"""
    value: str = Field(..., max_length=50, description="Reference number")
    is_unique: bool = Field(True, description="Is unique in Tally")
    
    @field_validator('value')
    @classmethod
    def validate_reference(cls, v):
        if ' ' in v:
            raise ValueError('Reference number cannot contain spaces')
        if len(v) > 50:
            raise ValueError('Reference number too long (max 50 chars)')
        return v.upper().strip()

class ExtractedParameters(BaseModel):
    """Complete set of extracted and validated parameters"""
    customer_name: Optional[CustomerName] = None
    amount: Optional[Amount] = None
    date: Optional[InvoiceDate] = None
    gst_rate: Optional[GstRate] = None
    ledger_code: Optional[LedgerCode] = None
    description: Optional[Description] = None
    reference_number: Optional[ReferenceNumber] = None
    
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    missing_params: List[str] = Field(default_factory=list, description="Missing required parameters")
    
    def is_valid(self) -> bool:
        """Check if all validations passed"""
        return len(self.errors) == 0 and len(self.missing_params) == 0
    
    def add_error(self, error: str):
        """Add validation error"""
        if error not in self.errors:
            self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        if warning not in self.warnings:
            self.warnings.append(warning)
    
    def add_missing(self, param: str):
        """Add missing parameter"""
        if param not in self.missing_params:
            self.missing_params.append(param)
