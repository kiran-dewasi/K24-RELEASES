from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Dict, Any
from datetime import datetime
import calendar

from backend.database import get_db, Voucher, Ledger
from backend.dependencies import get_api_key

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/sales-register", dependencies=[Depends(get_api_key)])
def get_sales_register(year: int = None, db: Session = Depends(get_db)):
    """
    Get Monthly Sales Summary.
    Returns list of months with total sales amount and voucher count.
    """
    if not year:
        year = datetime.now().year

    # Query: Sum amount by Month for 'Sales' vouchers
    # SQLite specific date extraction might vary, assuming standard datetime storage
    # For MVP with SQLite, we might need to fetch and aggregate in Python if date functions are tricky
    # But let's try SQLAlchemy extract first.
    
    results = db.query(
        extract('month', Voucher.date).label('month'),
        func.sum(Voucher.amount).label('total_amount'),
        func.count(Voucher.id).label('count')
    ).filter(
        extract('year', Voucher.date) == year,
        Voucher.voucher_type == 'Sales'
    ).group_by(extract('month', Voucher.date)).all()

    # Format response
    monthly_data = []
    for r in results:
        monthly_data.append({
            "month_num": int(r.month),
            "month_name": calendar.month_name[int(r.month)],
            "total_amount": r.total_amount,
            "voucher_count": r.count
        })
    
    # Fill missing months with 0
    existing_months = {d['month_num'] for d in monthly_data}
    for i in range(1, 13):
        if i not in existing_months:
            monthly_data.append({
                "month_num": i,
                "month_name": calendar.month_name[i],
                "total_amount": 0.0,
                "voucher_count": 0
            })
    
    # Sort by month
    monthly_data.sort(key=lambda x: x['month_num'])
    
    return {
        "year": year,
        "total_sales": sum(d['total_amount'] for d in monthly_data),
        "monthly_data": monthly_data
    }

@router.get("/purchase-register", dependencies=[Depends(get_api_key)])
def get_purchase_register(year: int = None, db: Session = Depends(get_db)):
    """
    Get Monthly Purchase Summary.
    """
    if not year:
        year = datetime.now().year

    results = db.query(
        extract('month', Voucher.date).label('month'),
        func.sum(Voucher.amount).label('total_amount'),
        func.count(Voucher.id).label('count')
    ).filter(
        extract('year', Voucher.date) == year,
        Voucher.voucher_type == 'Purchase'
    ).group_by(extract('month', Voucher.date)).all()

    monthly_data = []
    for r in results:
        monthly_data.append({
            "month_num": int(r.month),
            "month_name": calendar.month_name[int(r.month)],
            "total_amount": r.total_amount,
            "voucher_count": r.count
        })
    
    existing_months = {d['month_num'] for d in monthly_data}
    for i in range(1, 13):
        if i not in existing_months:
            monthly_data.append({
                "month_num": i,
                "month_name": calendar.month_name[i],
                "total_amount": 0.0,
                "voucher_count": 0
            })
    
    monthly_data.sort(key=lambda x: x['month_num'])
    
    return {
        "year": year,
        "total_purchase": sum(d['total_amount'] for d in monthly_data),
        "monthly_data": monthly_data
    }

@router.get("/cash-book", dependencies=[Depends(get_api_key)])
def get_cash_book(db: Session = Depends(get_db)):
    """
    Get Cash-in-Hand Balance and recent cash transactions.
    """
    # 1. Find Cash Ledger(s)
    # Usually named 'Cash' or under group 'Cash-in-hand'
    # For MVP, we look for ledger named 'Cash'
    cash_ledger = db.query(Ledger).filter(Ledger.name.ilike("Cash")).first()
    
    if not cash_ledger:
        return {"balance": 0.0, "transactions": []}

    # 2. Get recent vouchers involving Cash
    # This is tricky without line-item detail in Shadow DB.
    # We'll approximate: Vouchers where party_name is 'Cash' (Contra/Payment)
    # OR Vouchers where type is Receipt/Payment (implies cash/bank)
    
    # For now, return the closing balance from Ledger sync
    return {
        "ledger_name": cash_ledger.name,
        "current_balance": cash_ledger.closing_balance,
        "last_synced": cash_ledger.last_synced
    }

@router.get("/balance-sheet", dependencies=[Depends(get_api_key)])
def get_balance_sheet(db: Session = Depends(get_db)):
    """
    Get Balance Sheet Summary (Simplified for MVP).
    Aggregates Ledgers by Group (Assets vs Liabilities).
    """
    # In a real Tally sync, we'd have 'Parent' field in Ledger table.
    # We assume:
    # Assets: Groups starting with 'Current Assets', 'Fixed Assets', 'Bank Accounts', 'Cash-in-hand'
    # Liabilities: 'Current Liabilities', 'Loans', 'Capital Account'
    
    # Fetch all ledgers
    ledgers = db.query(Ledger).all()
    
    assets = []
    liabilities = []
    
    total_assets = 0.0
    total_liabilities = 0.0
    
    for l in ledgers:
        # Heuristic classification based on Parent (if available) or Name
        # This is fragile without a proper Chart of Accounts tree, but works for MVP
        parent = (l.parent or "").lower()
        name = l.name.lower()
        
        amount = l.closing_balance or 0.0
        
        # Tally Logic: Debit balance is usually Asset, Credit is Liability
        # But Tally returns closing balance as signed or with Dr/Cr flag.
        # Here we assume positive = Debit (Asset), negative = Credit (Liability)
        # Adjust based on your actual data ingestion logic in SyncEngine
        
        if "asset" in parent or "cash" in parent or "bank" in parent or "debtor" in parent:
            assets.append({"name": l.name, "amount": abs(amount), "group": l.parent})
            total_assets += abs(amount)
        elif "liabilit" in parent or "capital" in parent or "loan" in parent or "creditor" in parent:
            liabilities.append({"name": l.name, "amount": abs(amount), "group": l.parent})
            total_liabilities += abs(amount)
        else:
            # Fallback: Positive = Asset, Negative = Liability
            if amount >= 0:
                assets.append({"name": l.name, "amount": amount, "group": "Other Assets"})
                total_assets += amount
            else:
                liabilities.append({"name": l.name, "amount": abs(amount), "group": "Other Liabilities"})
                total_liabilities += abs(amount)

    return {
        "assets": sorted(assets, key=lambda x: x['amount'], reverse=True),
        "liabilities": sorted(liabilities, key=lambda x: x['amount'], reverse=True),
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_difference": total_assets - total_liabilities # Should be 0 in perfect books
    }

@router.get("/profit-loss", dependencies=[Depends(get_api_key)])
def get_profit_loss(db: Session = Depends(get_db)):
    """
    Get Profit & Loss Statement (Simplified).
    Income vs Expenses.
    """
    # Fetch Income/Expense Vouchers or Ledgers
    # Better to use Vouchers for P&L as it's period-based
    
    year = datetime.now().year
    
    # 1. Income (Sales)
    sales = db.query(func.sum(Voucher.amount)).filter(
        Voucher.voucher_type == 'Sales',
        extract('year', Voucher.date) == year
    ).scalar() or 0.0
    
    # 2. Expenses (Purchase + Payments)
    # This is a rough approximation. Real P&L needs Ledger grouping (Direct/Indirect Expenses)
    purchases = db.query(func.sum(Voucher.amount)).filter(
        Voucher.voucher_type == 'Purchase',
        extract('year', Voucher.date) == year
    ).scalar() or 0.0
    
    # 3. Net Profit
    net_profit = sales - purchases
    
    return {
        "income": {
            "Sales Accounts": sales,
            "Direct Income": 0.0, # Placeholder
            "Indirect Income": 0.0 # Placeholder
        },
        "expenses": {
            "Purchase Accounts": purchases,
            "Direct Expenses": 0.0,
            "Indirect Expenses": 0.0
        },
        "total_income": sales,
        "total_expenses": purchases,
        "net_profit": net_profit
    }
