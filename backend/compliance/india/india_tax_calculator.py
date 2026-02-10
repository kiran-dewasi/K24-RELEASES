"""
K24 Indian Compliance - Tax Calculator
=======================================
Calculate GST, TDS, RCM, and other Indian taxes.
"""

from typing import Tuple, Dict
from decimal import Decimal

class IndiaTaxCalculator:
    """Calculator for Indian taxes"""
    
    # GST rates by category (simplified)
    GST_RATES = {
        "ESSENTIAL": 5.0,    # Food, medicine
        "REGULAR": 12.0,     # Stationery
        "STANDARD": 18.0,    # Services, transport
        "LUXURY": 28.0,      # Cosmetics, high-end
        "EXEMPT": 0.0        # Exports
    }
    
    # TDS rates by section
    TDS_RATES = {
        "194C": 0.01,   # Contractor (1%)
        "194J": 0.10,   # Professional (10%)
        "194N_20L": 0.02,  # Cash > 20L (2%)
        "194N_1CR": 0.05,  # Cash > 1Cr (5%)
        "194O": 0.001,  # E-commerce (0.1%)
    }
    
    @staticmethod
    def calculate_gst(
        amount: float,
        rate: float,
        state_from: str = "MH",
        state_to: str = "MH",
        item_type: str = "STANDARD"
    ) -> Dict[str, float]:
        """
        Calculate GST amount and split into CGST/SGST or IGST.
        
        Args:
            amount: Taxable amount (before GST)
            rate: GST rate percentage
            state_from: Seller's state code
            state_to: Buyer's state code
            item_type: Item category
            
        Returns:
            Dict with GST breakdown
            
        Example:
            >>> calculate_gst(10000, 18, "MH", "MH")
            {'cgst': 900, 'sgst': 900, 'igst': 0, 'total_gst': 1800, 'total_amount': 11800}
        """
        gst_amount = amount * (rate / 100)
        
        # Same state: CGST + SGST
        if state_from == state_to:
            cgst = gst_amount / 2
            sgst = gst_amount / 2
            return {
                "cgst": round(cgst, 2),
                "sgst": round(sgst, 2),
                "igst": 0.0,
                "total_gst": round(gst_amount, 2),
                "taxable_amount": round(amount, 2),
                "total_amount": round(amount + gst_amount, 2)
            }
        else:
            # Different state: IGST
            return {
                "cgst": 0.0,
                "sgst": 0.0,
                "igst": round(gst_amount, 2),
                "total_gst": round(gst_amount, 2),
                "taxable_amount": round(amount, 2),
                "total_amount": round(amount + gst_amount, 2)
            }
    
    @staticmethod
    def calculate_tds(amount: float, payment_type: str, section: str = "194C") -> Dict[str, float]:
        """
        Calculate TDS amount.
        
        Args:
            amount: Payment amount
            payment_type: Type of payment (CONTRACTOR, PROFESSIONAL, etc.)
            section: TDS section
            
        Returns:
            Dict with TDS details
            
        Example:
            >>> calculate_tds(100000, "CONTRACTOR", "194C")
            {'tds_amount': 1000, 'net_payment': 99000, 'section': '194C', 'rate': 1.0}
        """
        # Determine section if not provided
        if not section:
            if payment_type == "CONTRACTOR":
                section = "194C"
            elif payment_type == "PROFESSIONAL":
                section = "194J"
        
        rate = IndiaTaxCalculator.TDS_RATES.get(section, 0.01)
        tds_amount = amount * rate
        net_payment = amount - tds_amount
        
        return {
            "tds_amount": round(tds_amount, 2),
            "net_payment": round(net_payment, 2),
            "gross_amount": round(amount, 2),
            "section": section,
            "rate": rate * 100  # Percentage
        }
    
    @staticmethod
    def calculate_rcm(amount: float, gst_rate: float = 18.0) -> Dict[str, float]:
        """
        Calculate Reverse Charge Mechanism (RCM) GST.
        
        Args:
            amount: Purchase amount from unregistered supplier
            gst_rate: Applicable GST rate
            
        Returns:
            Dict with RCM details
            
        Example:
            >>> calculate_rcm(10000, 18)
            {'rcm_gst': 1800, 'total_payment': 10000, 'gst_payable_to_govt': 1800}
        """
        rcm_gst = amount * (gst_rate / 100)
        
        return {
            "rcm_gst": round(rcm_gst, 2),
            "total_payment_to_supplier": round(amount, 2),  # Pay supplier without GST
            "gst_payable_to_govt": round(rcm_gst, 2),  # Pay separately to govt
            "total_outflow": round(amount + rcm_gst, 2),
            "itc_claimable": round(rcm_gst, 2)  # Can claim ITC if eligible
        }
    
    @staticmethod
    def calculate_igst_vs_cgst_sgst(amount: float, rate: float, state_from: str, state_to: str) -> Dict[str, float]:
        """
        Determine whether to use IGST or CGST+SGST based on state.
        
        Args:
            amount: Taxable amount
            rate: GST rate
            state_from: Seller state
            state_to: Buyer state
            
        Returns:
            Dict with tax split
        """
        return IndiaTaxCalculator.calculate_gst(amount, rate, state_from, state_to)
    
    @staticmethod
    def suggest_gst_rate(item_type: str) -> float:
        """
        Suggest appropriate GST rate based on item type.
        
        Args:
            item_type: Category of item
            
        Returns:
            Suggested GST rate
        """
        return IndiaTaxCalculator.GST_RATES.get(item_type.upper(), 18.0)
    
    @staticmethod
    def calculate_composition_tax(turnover: float) -> Dict[str, float]:
        """
        Calculate tax under Composition Scheme.
        
        Args:
            turnover: Annual turnover
            
        Returns:
            Dict with composition tax details
        """
        # Composition rate: 1% for goods, 6% for restaurants, 0.5% for manufacturers
        composition_rate = 0.01  # 1% for goods (simplified)
        tax_amount = turnover * composition_rate
        
        return {
            "composition_tax": round(tax_amount, 2),
            "turnover": round(turnover, 2),
            "rate": composition_rate * 100,
            "itc_allowed": False,  # No ITC under composition
            "filing": "Quarterly GSTR-4"
        }

# Global instance
calculator = IndiaTaxCalculator()

def calculate_gst(amount: float, rate: float, state_from: str = "MH", state_to: str = "MH") -> Dict[str, float]:
    return calculator.calculate_gst(amount, rate, state_from, state_to)

def calculate_tds(amount: float, payment_type: str, section: str = "194C") -> Dict[str, float]:
    return calculator.calculate_tds(amount, payment_type, section)

def calculate_rcm(amount: float, gst_rate: float = 18.0) -> Dict[str, float]:
    return calculator.calculate_rcm(amount, gst_rate)
