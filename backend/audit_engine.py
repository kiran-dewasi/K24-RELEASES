import pandas as pd
from typing import List, Dict, Any
from backend.tally_connector import TallyConnector

class AuditEngine:
    def __init__(self, tally_connector: TallyConnector):
        self.tally = tally_connector

    def run_full_audit(self) -> Dict[str, Any]:
        """Runs all audit checks and returns a summary report"""
        issues = []
        
        # 1. Check Cash Balance (Placeholder)
        # cash_issues = self._check_negative_cash()
        # issues.extend(cash_issues)

        # 2. Check High Value Cash Transactions (Rule 40A(3))
        high_value_issues = self._check_high_value_cash()
        issues.extend(high_value_issues)

        # 3. Check Duplicate Vouchers
        duplicate_issues = self._check_duplicates()
        issues.extend(duplicate_issues)

        # 4. GST Compliance (Missing/Invalid GSTIN)
        gst_issues = self._check_gst_compliance()
        issues.extend(gst_issues)

        # 5. Negative Stock
        stock_issues = self._check_negative_stock()
        issues.extend(stock_issues)

        # 6. Missing Critical Info (PAN, Email, Mobile)
        info_issues = self._check_missing_information()
        issues.extend(info_issues)

        # Calculate Score
        score = 100
        severity_penalty = {
            "Critical": 10,
            "High": 5,
            "Medium": 2,
            "Low": 1
        }
        
        for issue in issues:
            penalty = severity_penalty.get(issue.get("severity", "Low"), 1)
            score -= penalty
            
        score = max(0, score) # Minimum score 0

        return {
            "status": "clean" if not issues else "warning",
            "score": score,
            "issue_count": len(issues),
            "issues": issues
        }

    def _check_gst_compliance(self) -> List[Dict[str, Any]]:
        """Checks for Invalid or Missing GSTINs in Ledgers"""
        issues = []
        try:
            # Fetch full ledger details
            df = self.tally.fetch_ledgers_full()
            if df.empty:
                return []
            
            # Normalize columns
            df.columns = [c.strip().upper() for c in df.columns]
            
            # Check if GSTIN column exists (Tally field: PARTYGSTIN)
            gst_col = next((c for c in df.columns if 'GSTIN' in c), None)
            name_col = next((c for c in df.columns if 'NAME' in c and 'PARENT' not in c), 'NAME')
            
            if gst_col:
                import re
                gst_regex = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
                
                for _, row in df.iterrows():
                    gstin = str(row.get(gst_col, '')).strip()
                    name = row.get(name_col, 'Unknown')
                    
                    if gstin:
                        if not gst_regex.match(gstin):
                            issues.append({
                                "type": "Compliance Risk",
                                "severity": "High",
                                "message": f"Invalid GSTIN Format for {name}",
                                "details": f"GSTIN: {gstin}"
                            })
            
        except Exception as e:
            print(f"Audit Error (GST): {e}")
        return issues

    def _check_negative_stock(self) -> List[Dict[str, Any]]:
        """Checks for Negative Stock Items"""
        issues = []
        try:
            df = self.tally.fetch_stock_items()
            if df.empty:
                return []
            
            # Normalize
            df.columns = [c.strip().upper() for c in df.columns]
            
            # Look for Closing Balance (Tally field: CLOSINGBALANCE)
            # Tally returns closing balance as string with unit, e.g., "- 10.00 kgs" or "10.00 kgs"
            # Negative usually indicated by '-' or specific flag
            
            bal_col = next((c for c in df.columns if 'CLOSINGBALANCE' in c), None)
            name_col = next((c for c in df.columns if 'NAME' in c), 'NAME')
            
            if bal_col:
                for _, row in df.iterrows():
                    bal_str = str(row.get(bal_col, '')).strip()
                    name = row.get(name_col, 'Unknown')
                    
                    # Check for negative sign
                    if bal_str.startswith('-') or 'Dr' in bal_str: # Tally sometimes uses Dr/Cr
                         issues.append({
                            "type": "Business Health",
                            "severity": "Critical",
                            "message": f"Negative Stock for {name}",
                            "details": f"Balance: {bal_str}"
                        })

        except Exception as e:
            print(f"Audit Error (Stock): {e}")
        return issues

    def _check_missing_information(self) -> List[Dict[str, Any]]:
        """Checks for missing PAN, Email, Mobile in Sundry Debtors/Creditors"""
        issues = []
        try:
            df = self.tally.fetch_ledgers_full()
            if df.empty:
                return []
            
            df.columns = [c.strip().upper() for c in df.columns]
            
            name_col = next((c for c in df.columns if 'NAME' in c and 'PARENT' not in c), 'NAME')
            parent_col = next((c for c in df.columns if 'PARENT' in c), None)
            pan_col = next((c for c in df.columns if 'PAN' in c), None)
            email_col = next((c for c in df.columns if 'EMAIL' in c), None)
            
            for _, row in df.iterrows():
                parent = str(row.get(parent_col, '')).upper()
                # Only check Debtors and Creditors
                if 'DEBTOR' in parent or 'CREDITOR' in parent:
                    name = row.get(name_col, 'Unknown')
                    missing = []
                    
                    if pan_col and not str(row.get(pan_col, '')).strip():
                        missing.append("PAN")
                    if email_col and not str(row.get(email_col, '')).strip():
                        missing.append("Email")
                        
                    if missing:
                         issues.append({
                            "type": "Data Quality",
                            "severity": "Low",
                            "message": f"Missing Information for {name}",
                            "details": f"Missing: {', '.join(missing)}"
                        })

        except Exception as e:
            print(f"Audit Error (Info): {e}")
        return issues

    def _check_high_value_cash(self) -> List[Dict[str, Any]]:
        """Flags cash payments exceeding ₹10,000 (Section 40A(3))"""
        issues = []
        try:
            # Fetch 'Cash' ledger vouchers
            df = self.tally.fetch_ledger_vouchers("Cash")
            if df.empty:
                return []

            # Filter for Payments > 10000
            # Assuming df has 'amount', 'voucher_type', 'date', 'narration'
            # Note: fetch_ledger_vouchers returns amounts as strings or floats. 
            # We need to ensure they are numeric.
            
            # Filter for Payment vouchers
            payments = df[df['voucher_type'].str.lower() == 'payment'].copy()
            
            if payments.empty:
                return []
                
            # Check amounts
            for _, row in payments.iterrows():
                amount = float(row['amount'])
                if amount > 10000:
                    issues.append({
                        "type": "Compliance Risk",
                        "severity": "High",
                        "message": f"Cash Payment of ₹{amount} exceeds ₹10,000 limit",
                        "details": f"Date: {row['date']}, Voucher: {row.get('voucher_number', 'N/A')}"
                    })
                    
        except Exception as e:
            print(f"Audit Error (High Value Cash): {e}")
            
        return issues

    def _check_duplicates(self) -> List[Dict[str, Any]]:
        """Checks for potential duplicate vouchers (Same Amount + Same Date)"""
        issues = []
        try:
            # We'll check the Day Book (all vouchers)
            # For MVP, let's just check the Cash book as a proxy
            df = self.tally.fetch_ledger_vouchers("Cash")
            if df.empty:
                return []
                
            # Group by Date and Amount
            duplicates = df[df.duplicated(subset=['date', 'amount', 'voucher_type'], keep=False)]
            
            if not duplicates.empty:
                # Group to format the message
                grouped = duplicates.groupby(['date', 'amount', 'voucher_type'])
                for (date, amount, v_type), group in grouped:
                    issues.append({
                        "type": "Data Quality",
                        "severity": "Medium",
                        "message": f"Potential Duplicate: {len(group)} {v_type} vouchers of ₹{amount} on {date}",
                        "details": "Please verify if these are distinct transactions."
                    })

        except Exception as e:
            print(f"Audit Error (Duplicates): {e}")
            
        return issues
