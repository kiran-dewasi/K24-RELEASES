"""
K24 Indian Compliance - Calendar
=================================
Key compliance dates and deadlines for Indian SMBs.
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple
from calendar import monthrange

class IndiaComplianceCalendar:
    """Track key compliance deadlines for Indian businesses"""
    
    # Monthly GST deadlines
    GSTR1_DAY = 11   # Sales return
    GSTR2B_DAY = 15  # Auto-populated purchase return
    GSTR3B_DAY = 20  # Summary return
    GST_PAYMENT_DAY = 20  # Tax payment
    
    # TDS deadlines
    TDS_DEPOSIT_DAY = 7  # Deposit TDS by 7th of next month
    
    # Annual deadlines
    GSTR9_DEADLINE = (12, 31)  # Annual return (31st Dec)
    ITR_DEADLINE = (7, 31)     # Income tax return (31st July)
    
    @staticmethod
    def get_upcoming_deadlines(today: date = None, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming compliance deadlines.
        
        Args:
            today: Reference date (defaults to today)
            days_ahead: Look ahead this many days
            
        Returns:
            List of upcoming deadlines
            
        Example:
            >>> get_upcoming_deadlines()
            [{'date': '2025-12-11', 'type': 'GSTR-1', 'description': '...'}]
        """
        if today is None:
            today = date.today()
        
        deadlines = []
        end_date = today + timedelta(days=days_ahead)
        
        # Check each month in the range
        current = today
        while current <= end_date:
            month = current.month
            year = current.year
            
            # GSTR-1 (11th of month)
            gstr1_date = date(year, month, IndiaComplianceCalendar.GSTR1_DAY)
            if today <= gstr1_date <= end_date:
                deadlines.append({
                    "date": gstr1_date,
                    "type": "GSTR-1",
                    "description": "File GSTR-1 sales return",
                    "severity": "HIGH",
                    "penalty": "₹200/day up to ₹5,000"
                })
            
            # GSTR-2B (15th of month)
            gstr2b_date = date(year, month, IndiaComplianceCalendar.GSTR2B_DAY)
            if today <= gstr2b_date <= end_date:
                deadlines.append({
                    "date": gstr2b_date,
                    "type": "GSTR-2B",
                    "description": "Review auto-populated purchase return",
                    "severity": "INFO",
                    "penalty": "N/A (auto-generated)"
                })
            
            # GSTR-3B (20th of month)
            gstr3b_date = date(year, month, IndiaComplianceCalendar.GSTR3B_DAY)
            if today <= gstr3b_date <= end_date:
                deadlines.append({
                    "date": gstr3b_date,
                    "type": "GSTR-3B",
                    "description": "File GSTR-3B summary return & pay tax",
                    "severity": "CRITICAL",
                    "penalty": "₹200/day + late fees on tax"
                })
            
            # TDS Deposit (7th of month)
            tds_date = date(year, month, IndiaComplianceCalendar.TDS_DEPOSIT_DAY)
            if today <= tds_date <= end_date:
                deadlines.append({
                    "date": tds_date,
                    "type": "TDS",
                    "description": "Deposit TDS to government",
                    "severity": "HIGH",
                    "penalty": "1% interest per month"
                })
            
            # Move to next month
            if month == 12:
                current = date(year + 1, 1, 1)
            else:
                current = date(year, month + 1, 1)
        
        # Annual deadlines
        # GSTR-9 (31st Dec)
        gstr9_date = date(today.year, IndiaComplianceCalendar.GSTR9_DEADLINE[0], IndiaComplianceCalendar.GSTR9_DEADLINE[1])
        if today <= gstr9_date <= end_date:
            deadlines.append({
                "date": gstr9_date,
                "type": "GSTR-9",
                "description": "File annual GST return (if turnover > ₹1Cr)",
                "severity": "CRITICAL",
                "penalty": "₹200/day + penalties"
            })
        
        # ITR (31st July)
        itr_date = date(today.year, IndiaComplianceCalendar.ITR_DEADLINE[0], IndiaComplianceCalendar.ITR_DEADLINE[1])
        if today <= itr_date <= end_date:
            deadlines.append({
                "date": itr_date,
                "type": "ITR",
                "description": "File income tax return",
                "severity": "CRITICAL",
                "penalty": "₹5,000 late fee + 1% interest per month"
            })
        
        # Sort by date
        deadlines.sort(key=lambda x: x["date"])
        
        return deadlines
    
    @staticmethod
    def get_next_deadline(deadline_type: str, today: date = None) -> Tuple[date, int]:
        """
        Get next deadline for a specific compliance type.
        
        Args:
            deadline_type: Type (GSTR-1, GSTR-3B, TDS, etc.)
            today: Reference date
            
        Returns:
            (deadline_date, days_until)
        """
        if today is None:
            today = date.today()
        
        month = today.month
        year = today.year
        
        if deadline_type == "GSTR-1":
            day = IndiaComplianceCalendar.GSTR1_DAY
        elif deadline_type == "GSTR-3B":
            day = IndiaComplianceCalendar.GSTR3B_DAY
        elif deadline_type == "TDS":
            day = IndiaComplianceCalendar.TDS_DEPOSIT_DAY
        else:
            return (None, 0)
        
        # Calculate deadline date
        deadline = date(year, month, day)
        
        # If already passed this month, use next month
        if today > deadline:
            if month == 12:
                deadline = date(year + 1, 1, day)
            else:
                deadline = date(year, month + 1, day)
        
        days_until = (deadline - today).days
        
        return (deadline, days_until)
    
    @staticmethod
    def is_near_deadline(deadline_type: str, warning_days: int = 3, today: date = None) -> Tuple[bool, str]:
        """
        Check if a deadline is approaching.
        
        Args:
            deadline_type: Type of deadline
            warning_days: Warn if within this many days
            today: Reference date
            
        Returns:
            (is_near, message)
        """
        deadline, days_until = IndiaComplianceCalendar.get_next_deadline(deadline_type, today)
        
        if deadline and days_until <= warning_days:
            return (
                True,
                f"{deadline_type} due in {days_until} days ({deadline.strftime('%d %b %Y')})"
            )
        
        return (False, "")
    
    @staticmethod
    def get_fy_dates(fy_year: int = None) -> Tuple[date, date]:
        """
        Get financial year start and end dates (India: April-March).
        
        Args:
            fy_year: Financial year (e.g., 2025 for FY 2024-25)
            
        Returns:
            (fy_start, fy_end)
        """
        if fy_year is None:
            today = date.today()
            if today.month >= 4:
                fy_year = today.year
            else:
                fy_year = today.year - 1
        
        fy_start = date(fy_year, 4, 1)
        fy_end = date(fy_year + 1, 3, 31)
        
        return (fy_start, fy_end)

# Global instance
calendar = IndiaComplianceCalendar()

def get_upcoming_deadlines(days_ahead: int = 30) -> List[Dict]:
    return calendar.get_upcoming_deadlines(days_ahead=days_ahead)

def is_near_deadline(deadline_type: str, warning_days: int = 3) -> Tuple[bool, str]:
    return calendar.is_near_deadline(deadline_type, warning_days)
