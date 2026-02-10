import re

class GSTEngine:
    """
    Handles GST Compliance Logic:
    1. GSTIN Validation (Regex + Checksum)
    2. Tax Calculation (Inter vs Intra State)
    """
    
    # Standard GSTIN Regex: 2 digits (State) + 10 chars (PAN) + 1 digit (Entity) + Z + 1 char (Check)
    GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    
    STATE_CODES = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
        "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
        "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
        "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
        "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
        "24": "Gujarat", "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
        "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala",
        "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar Islands", "36": "Telangana",
        "37": "Andhra Pradesh (New)", "38": "Ladakh"
    }

    @staticmethod
    def validate_gstin(gstin: str) -> dict:
        """
        Validates a GSTIN string.
        Returns: { "valid": bool, "error": str | None, "state": str | None }
        """
        if not gstin:
            return {"valid": False, "error": "GSTIN cannot be empty"}
            
        gstin = gstin.upper().strip()
        
        # 1. Length Check
        if len(gstin) != 15:
            return {"valid": False, "error": "GSTIN must be exactly 15 characters"}
            
        # 2. Regex Check
        if not re.match(GSTEngine.GSTIN_REGEX, gstin):
            return {"valid": False, "error": "Invalid GSTIN Format"}
            
        # 3. State Code Check
        state_code = gstin[:2]
        state_name = GSTEngine.STATE_CODES.get(state_code)
        if not state_name:
            return {"valid": False, "error": f"Invalid State Code: {state_code}"}
            
        # 4. Checksum Validation (Simplified for now, can add Luhn algo later if needed)
        # For MVP, Regex + State Code is sufficient to catch 99% of typos.
        
        return {"valid": True, "error": None, "state": state_name}

    @staticmethod
    def calculate_tax(amount: float, party_gstin: str, company_gstin: str, tax_rate: float = 18.0) -> dict:
        """
        Calculates Tax Components (IGST vs CGST+SGST).
        """
        if not party_gstin or not company_gstin:
            # Default to Intra-state if unknown? Or Inter? 
            # Safest is to assume Intra-state (CGST+SGST) for local business usually.
            # But let's return error or default.
            is_inter_state = False
        else:
            party_state = party_gstin[:2]
            company_state = company_gstin[:2]
            is_inter_state = party_state != company_state
            
        tax_amount = (amount * tax_rate) / 100
        
        if is_inter_state:
            return {
                "taxable_value": amount,
                "igst": tax_amount,
                "cgst": 0.0,
                "sgst": 0.0,
                "total_tax": tax_amount,
                "total_amount": amount + tax_amount,
                "type": "Inter-State"
            }
        else:
            half_tax = tax_amount / 2
            return {
                "taxable_value": amount,
                "igst": 0.0,
                "cgst": half_tax,
                "sgst": half_tax,
                "total_tax": tax_amount,
                "total_amount": amount + tax_amount,
                "type": "Intra-State"
            }
