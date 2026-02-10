from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import os

from backend.database import get_db, Voucher, Ledger
from backend.dependencies import get_api_key
from backend.sync_engine import sync_engine

router = APIRouter(prefix="/operations", tags=["operations"])

# Check if Tally is in EDU mode
TALLY_EDU_MODE = os.getenv("TALLY_EDU_MODE", "false").lower() == "true"

@router.post("/receipt", dependencies=[Depends(get_api_key)])
def create_receipt(data: Dict[str, Any]):
    """
    Create a Receipt Voucher (Money In).
    Required: party_name, amount, bank_cash_ledger
    Optional: date, narration
    """
    try:
        # 1. Convert date from YYYY-MM-DD to YYYYMMDD
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if TALLY_EDU_MODE:
                # EDU mode: force day to 01 (use current year/month)
                voucher_date = date_obj.strftime("%Y%m01")
            else:
                # Premium Tally: use actual date
                voucher_date = date_obj.strftime("%Y%m%d")
        except:
            # Fallback: use current month with day=01
            voucher_date = datetime.now().strftime("%Y%m01")
        
        voucher_data = {
            "voucher_type": "Receipt",
            "date": voucher_date,
            "party_name": data["party_name"],
            "amount": float(data["amount"]),
            "narration": data.get("narration", f"Receipt from {data['party_name']}"),
            "deposit_to": data.get("bank_cash_ledger", "Cash")
        }
        
        # 2. Push to Tally via Sync Engine
        result = sync_engine.push_voucher_safe(voucher_data)
        
        if result["success"]:
            return {"status": "success", "message": "Receipt created successfully", "id": result.get("voucher_id")}
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except KeyError as k:
        raise HTTPException(status_code=400, detail=f"Missing field: {k}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment", dependencies=[Depends(get_api_key)])
def create_payment(data: Dict[str, Any]):
    """
    Create a Payment Voucher (Money Out).
    Required: party_name, amount, bank_cash_ledger
    """
    try:
        # 1. Convert date (same logic as Receipt)
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if TALLY_EDU_MODE:
                voucher_date = date_obj.strftime("%Y%m01")
            else:
                voucher_date = date_obj.strftime("%Y%m%d")
        except:
            voucher_date = datetime.now().strftime("%Y%m01")
        
        voucher_data = {
            "voucher_type": "Payment",
            "date": voucher_date,
            "party_name": data["party_name"],
            "amount": float(data["amount"]),
            "narration": data.get("narration", f"Payment to {data['party_name']}"),
            "deposit_to": data.get("bank_cash_ledger", "Cash")
        }
        
        result = sync_engine.push_voucher_safe(voucher_data)
        
        if result["success"]:
            return {"status": "success", "message": "Payment created successfully", "id": result.get("voucher_id")}
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except KeyError as k:
        raise HTTPException(status_code=400, detail=f"Missing field: {k}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
