from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from database import get_db, Ledger, Voucher
from dependencies import get_api_key
from auth import get_current_tenant_id

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("/detailed")
async def get_contacts_detailed(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get detailed contact list with financials.
    Calculates total sales, purchases, and last transaction for each ledger.
    """
    # 1. Fetch all ledgers for this tenant
    # Filter for relevant groups? Usually Sundry Debtors/Creditors.
    # For now fetching ALL ledgers might be too much if it includes expense ledgers.
    # Let's filter by groups that likely represent contacts if possible, or fetch all and let frontend filter?
    # Better: Filter by parent name containing "Sundry" or "Debtor" or "Creditor".
    # Or just return all and let frontend decide.
    # Given the prompt, let's fetch all but maybe prioritization on Debtors/Creditors.
    
    ledgers = db.query(Ledger).filter(
        Ledger.tenant_id == tenant_id
    ).all()

    result = []
    
    # Pre-fetch vouchers to minimize N+1 queries? 
    # With many ledgers, N+1 is bad.
    # But for MVP, per-ledger query is simple. 
    # Optimization: Use a single aggregation query grouping by party_name.
    
    # Optimized Query:
    # Sales Totals
    sales_stats = db.query(
        Voucher.party_name, 
        func.sum(Voucher.amount).label('total')
    ).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.in_(["Sales", "Sales Order"])
    ).group_by(Voucher.party_name).all()
    
    sales_map = {r.party_name: r.total for r in sales_stats}
    
    # Purchase Totals
    purch_stats = db.query(
        Voucher.party_name, 
        func.sum(Voucher.amount).label('total')
    ).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.in_(["Purchase", "Purchase Order"])
    ).group_by(Voucher.party_name).all()
    
    purch_map = {r.party_name: r.total for r in purch_stats}
    
    # Last Transactions (Tricky to batch efficiently without subqueries/window functions)
    # We'll fetch last tx per ledger for now or leave it if performance hit is okay.
    # Let's do lazy fetch just for the visible ones? No, API returns all.
    # We will do a generic last date per party query.
    
    last_dates = db.query(
        Voucher.party_name,
        func.max(Voucher.date).label('last_date')
    ).filter(
        Voucher.tenant_id == tenant_id
    ).group_by(Voucher.party_name).all()
    
    date_map = {r.party_name: r.last_date for r in last_dates}
    
    # Now build result
    for ledger in ledgers:
        # Determine type
        l_group = (ledger.parent or "").lower()
        contact_type = "Other"
        if "debtor" in l_group:
            contact_type = "Customer"
        elif "creditor" in l_group:
            contact_type = "Supplier"
            
        # Skip if it's likely a system ledger (Cash, Profit & Loss, etc) unless it has transactions?
        # User wants "Contacts". Usually Customers/Suppliers.
        if contact_type == "Other" and ledger.name.lower() not in sales_map and ledger.name.lower() not in purch_map:
            # Maybe skip non-business ledgers to keep list clean?
            # Let's keep them if they are explicitly Debtors/Creditors.
            pass

        s_total = sales_map.get(ledger.name, 0.0)
        p_total = purch_map.get(ledger.name, 0.0)
        
        # Check if we should include this ledger
        # Include if: Group is Debtor/Creditor OR has significant activity
        is_relevant = "debtor" in l_group or "creditor" in l_group or s_total > 0 or p_total > 0
        
        if is_relevant:
            result.append({
                "id": ledger.id,
                "name": ledger.name,
                "group": ledger.parent,
                "type": contact_type,
                "phone": ledger.phone,
                "email": ledger.email,
                "gstin": ledger.gstin,
                "total_sales": s_total,
                "total_purchases": p_total,
                "outstanding": ledger.closing_balance, # Use actual ledger balance for accurate outstanding
                "last_transaction": date_map.get(ledger.name),
                "last_transaction_amount": 0 # Placeholder, hard to get without N+1
            })

    # Sort by activity (Sales + Purchases)
    result.sort(key=lambda x: x['total_sales'] + x['total_purchases'], reverse=True)
    
    return result

from pydantic import BaseModel
from fastapi import HTTPException

class ContactUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None

@router.put("/{contact_id}")
async def update_contact(
    contact_id: int, 
    update_data: ContactUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Update contact details (Phone/Email).
    """
    ledger = db.query(Ledger).filter(Ledger.id == contact_id, Ledger.tenant_id == tenant_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    if update_data.phone is not None:
        ledger.phone = update_data.phone
    if update_data.email is not None:
        ledger.email = update_data.email
        
    db.commit()
    return {"status": "success", "message": "Contact updated"}
