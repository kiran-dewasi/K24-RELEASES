from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database import get_db, Ledger, Voucher, StockItem
from auth import get_current_tenant_id
from dependencies import get_api_key

router = APIRouter(tags=["search"])


@router.get("/search/global")
async def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    tenant_id: str = "default" # Fallback to default for now
):
    """
    Search across Ledgers, Vouchers, and Items.
    Returns categorized results.
    """
    query = q.strip()
    results = {
        "ledgers": [],
        "vouchers": [],
        "items": []
    }
    
    if not query:
        return results

    # 1. Search Ledgers (Parties)
    ledgers = db.query(Ledger).filter(
        Ledger.tenant_id == tenant_id,
        or_(
            Ledger.name.ilike(f"%{query}%"),
            Ledger.alias.ilike(f"%{query}%"),
            Ledger.gstin.ilike(f"%{query}%"),
            Ledger.phone.ilike(f"%{query}%"),
            Ledger.email.ilike(f"%{query}%")
        )
    ).limit(5).all()

    for l in ledgers:
        results["ledgers"].append({
            "id": l.id,
            "name": l.name,
            "type": l.ledger_type,
            "balance": l.closing_balance,
            "group": l.parent
        })

    # 2. Search Vouchers (Transactions)
    # Search by Amount, Voucher No, Narration
    voucher_filters = [
        Voucher.voucher_number.ilike(f"%{query}%"),
        Voucher.party_name.ilike(f"%{query}%"),
        Voucher.narration.ilike(f"%{query}%")
    ]
    
    # Try parsing amount if digit
    try:
        amt = float(query.replace(",", ""))
        voucher_filters.append(Voucher.amount == amt)
    except:
        pass

    vouchers = db.query(Voucher).filter(
        Voucher.tenant_id == tenant_id,
        or_(*voucher_filters)
    ).order_by(Voucher.date.desc()).limit(5).all()

    for v in vouchers:
        results["vouchers"].append({
            "id": v.id,
            "date": v.date,
            "number": v.voucher_number,
            "party": v.party_name,
            "amount": v.amount,
            "type": v.voucher_type
        })
        
    # 3. Search Items
    items = db.query(StockItem).filter(
        StockItem.tenant_id == tenant_id,
        or_(
            StockItem.name.ilike(f"%{query}%"),
            StockItem.part_number.ilike(f"%{query}%"),
            StockItem.description.ilike(f"%{query}%")
        )
    ).limit(5).all()
    
    for i in items:
        results["items"].append({
            "id": i.id,
            "name": i.name,
            "stock": i.closing_balance,
            "rate": i.rate,
            "group": i.stock_group
        })

    return results
