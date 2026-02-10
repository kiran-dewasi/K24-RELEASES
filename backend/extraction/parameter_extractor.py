"""
K24 Parameter Extraction - Main Extractor
==========================================
Extract parameters from user messages with timeout and validation.
"""

import re
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import date
from backend.extraction.parameter_models import (
    ExtractedParameters, CustomerName, Amount, InvoiceDate, GstRate, Description
)
from backend.extraction.fuzzy_matcher import match_ledger_with_fallback, get_ledger_details

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5  # seconds

class ParameterExtractor:
    """Main parameter extraction engine"""
    
    # Regex patterns for extraction
    AMOUNT_PATTERNS = [
        r'(?:₹|rs\.?|rupees?)\s*([0-9,]+(?:\.[0-9]{2})?)',  # ₹50,000 or Rs. 5000
        r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:₹|rs\.?|rupees?)',  # 50000 Rs
        r'\b([0-9,]+(?:\.[0-9]{2})?)\s*(?:lakhs?|lacs?|l)\b',  # 5 lakhs or 5L
        r'\b([0-9,]+(?:\.[0-9]{2})?)\s*(?:crores?|cr)\b',  # 1 crore or 1Cr
        r'(?:for|amount|of)\s+([0-9,]+(?:\.[0-9]{2})?)',  # for 50000
    ]
    
    GST_PATTERNS = [
        r'(\d+)%?\s*gst',  # 18% GST or 18 GST
        r'gst\s*(\d+)%?',  # GST 18% or GST 18
        r'with\s+(\d+)%',  # with 18%
    ]
    
    DATE_PATTERNS = [
        r'(?:on|dated|date)\s+(\d{4}-\d{2}-\d{2})',  # on 2025-12-03
        r'(?:on|dated|date)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # on 03-12-2025
        r'\b(today|yesterday|tomorrow)\b',  # today
    ]
    
    @staticmethod
    def parse_amount(text: str) -> Optional[float]:
        """
        Parse amount from text, handling Indian number formats.
        
        Examples:
            "50000" -> 50000.0
            "5L" -> 500000.0
            "1Cr" -> 10000000.0
            "₹50,000" -> 50000.0
        """
        text_lower = text.lower().strip()
        
        # Handle lakhs and crores
        if 'lakh' in text_lower or 'lac' in text_lower or text_lower.endswith('l'):
            # 5 lakhs = 500,000
            num_str = re.sub(r'[^\d.]', '', text)
            try:
                return float(num_str) * 100000
            except:
                pass
        
        if 'crore' in text_lower or text_lower.endswith('cr'):
            # 1 crore = 10,000,000
            num_str = re.sub(r'[^\d.]', '', text)
            try:
                return float(num_str) * 10000000
            except:
                pass
        
        # Regular number
        num_str = re.sub(r'[^\d.]', '', text)
        try:
            return float(num_str)
        except:
            return None
    
    @staticmethod
    def extract_customer_name(message: str, intent: str) -> Optional[str]:
        """
        Extract customer/party name from message.
        
        Patterns:
            "invoice for ABC Corp" -> "ABC Corp"
            "payment from XYZ Ltd" -> "XYZ Ltd"
            "receipt for Reliance" -> "Reliance"
        """
        patterns = [
            r'(?:for|to|from)\s+([A-Z][\w\s&.-]+?)(?:\s+for|\s+of|\s+with|\s+\d|\s+₹|$)',
            r'(?:customer|party|ledger)\s+([A-Z][\w\s&.-]+?)(?:\s+for|\s+of|\s+with|\s+\d|\s+₹|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 2:  # Reasonable name length
                    return name
        
        return None
    
    async def extract_parameters(
        self,
        message: str,
        intent: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> ExtractedParameters:
        """
        Extract and validate all parameters from message.
        
        Args:
            message: User input message
            intent: Classified intent
            timeout: Max time in seconds
            
        Returns:
            ExtractedParameters object with extracted values and errors
            
        Example:
            >>> await extractor.extract_parameters(
            ...     "Create invoice for HDFC 50000 with 18% GST",
            ...     "CREATE_INVOICE"
            ... )
            ExtractedParameters(customer_name=..., amount=..., ...)
        """
        try:
            result = await asyncio.wait_for(
                self._do_extraction(message, intent),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Parameter extraction timeout after {timeout}s")
            result = ExtractedParameters()
            result.add_error(f"Extraction timeout after {timeout}s")
            return result
        except Exception as e:
            logger.error(f"Parameter extraction error: {e}")
            result = ExtractedParameters()
            result.add_error(f"Extraction error: {str(e)}")
            return result
    
    async def _do_extraction(self, message: str, intent: str) -> ExtractedParameters:
        """Internal extraction logic"""
        result = ExtractedParameters()
        
        # 1. Extract customer name
        customer_name_str = self.extract_customer_name(message, intent)
        if customer_name_str:
            await self._extract_and_validate_customer(customer_name_str, result)
        else:
            if 'CREATE' in intent or 'UPDATE' in intent:
                result.add_missing("customer_name")
        
        # 2. Extract amount
        amount_value = await self._extract_amount(message, result)
        if amount_value:
            # Validate reasonableness (if we have customer)
            if result.customer_name:
                await self._validate_amount_reasonableness(amount_value, result)
        else:
            if 'CREATE' in intent or 'UPDATE' in intent:
                result.add_missing("amount")
        
        # 3. Extract date
        date_value = self._extract_date(message)
        if date_value:
            try:
                result.date = InvoiceDate.from_string(date_value)
                if result.date.is_retroactive:
                    result.add_warning(f"This is a retroactive entry ({result.date.days_old} days old)")
            except ValueError as e:
                result.add_error(f"Invalid date: {str(e)}")
        else:
            # Default to today
            result.date = InvoiceDate(value=date.today(), is_today=True, days_old=0)
        
        # 4. Extract GST rate
        gst_value = self._extract_gst_rate(message, result)
        if gst_value is not None:
            try:
                result.gst_rate = GstRate(value=gst_value)
                # Suggest based on ledger type if available
                if result.customer_name and result.customer_name.ledger_id:
                    await self._validate_gst_rate(result)
            except ValueError as e:
                result.add_error(f"Invalid GST rate: {str(e)}")
        
        return result
    
    async def _extract_and_validate_customer(self, name: str, result: ExtractedParameters):
        """Extract and fuzzy match customer name"""
        matched_name, confidence, alternatives = match_ledger_with_fallback(name)
        
        if matched_name:
            # Exact or high-confidence match
            ledger_details = get_ledger_details(matched_name)
            result.customer_name = CustomerName(
                value=matched_name,
                ledger_id=str(ledger_details['id']) if ledger_details else None,
                confidence=confidence
            )
        elif alternatives:
            # Low confidence, suggest alternatives
            suggestions = ', '.join(alternatives)
            result.add_error(f"Ledger '{name}' not found. Did you mean: {suggestions}?")
            result.customer_name = CustomerName(
                value=name,
                confidence=confidence,
                alternatives=alternatives
            )
        else:
            result.add_error(f"Ledger '{name}' not found in Tally")
    
    async def _extract_amount(self, message: str, result: ExtractedParameters) -> Optional[float]:
        """Extract amount from message"""
        for pattern in self.AMOUNT_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                amount_value = self.parse_amount(amount_str)
                
                if amount_value:
                    try:
                        result.amount = Amount(value=amount_value)
                        return amount_value
                    except ValueError as e:
                        result.add_error(str(e))
                        return None
        
        return None
    
    async def _validate_amount_reasonableness(self, amount: float, result: ExtractedParameters):
        """Check if amount is reasonable for customer"""
        # TODO: Query average invoice amount from database
        # For now, just check very high amounts
        if amount > 1000000:  # 10L+
            result.add_warning(f"Amount ₹{amount/100000:.1f}L is very high. Please confirm.")
    
    def _extract_date(self, message: str) -> Optional[str]:
        """Extract date from message"""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_gst_rate(self, message: str, result: ExtractedParameters) -> Optional[float]:
        """Extract GST rate from message"""
        for pattern in self.GST_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    rate = float(match.group(1))
                    return rate
                except:
                    pass
        return None
    
    async def _validate_gst_rate(self, result: ExtractedParameters):
        """Validate GST rate against ledger type"""
        # TODO: Implement ledger type lookup and GST validation
        pass

# Global instance
_extractor: Optional[ParameterExtractor] = None

def get_extractor() -> ParameterExtractor:
    """Get or create global extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = ParameterExtractor()
    return _extractor

async def extract_parameters(
    message: str,
    intent: str,
    timeout: int = DEFAULT_TIMEOUT
) -> ExtractedParameters:
    """
    Convenience function for parameter extraction.
    
    Args:
        message: User input
        intent: Classified intent
        timeout: Max time in seconds
        
    Returns:
        ExtractedParameters object
    """
    extractor = get_extractor()
    return await extractor.extract_parameters(message, intent, timeout)
