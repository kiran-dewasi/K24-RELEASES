"""
Customer 360° Profile API
Salesforce-style complete customer view with all interactions, transactions, and insights.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_, desc
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from backend.database import get_db, Ledger, Voucher, Bill, StockMovement, StockItem
from backend.auth import get_current_tenant_id
from backend.dependencies import get_api_key

import logging

router = APIRouter(prefix="/customers", tags=["customers"])
logger = logging.getLogger("customers")


# --- Pydantic Response Models ---

class CustomerSummary(BaseModel):
    transaction_count: int
    total_sales: float
    total_receipts: float
    total_purchases: float
    total_payments: float
    first_transaction_date: Optional[str]
    last_transaction_date: Optional[str]
    outstanding_total: float
    overdue_total: float
    credit_days_avg: int
    payment_promptness: int


class OutstandingBill(BaseModel):
    bill_name: str
    amount: float
    due_date: Optional[str]
    overdue_days: int
    is_overdue: bool


class PaymentRecord(BaseModel):
    id: int
    date: str
    voucher_number: str
    amount: float
    narration: Optional[str]


class TopItem(BaseModel):
    item_name: str
    total_quantity: float
    total_value: float
    transaction_count: int
    avg_rate: float
    last_date: Optional[str]


class CustomerInsights(BaseModel):
    avg_credit_days: int
    payment_score: int
    health_score: int
    risk_level: str  # low, medium, high
    customer_tier: str  # platinum, gold, silver, bronze
    trend: str  # growing, stable, declining
    recommendations: List[str]


class Customer360Response(BaseModel):
    customer: Dict[str, Any]
    summary: Dict[str, Any]
    outstanding_bills: List[Dict]
    recent_payments: List[Dict]
    recent_transactions: List[Dict]
    top_items: List[Dict]
    monthly_trend: List[Dict]
    insights: Dict[str, Any]
    health_score: int


# --- Main 360° Endpoint ---

@router.get("/{customer_id}/360", response_model=Customer360Response, dependencies=[Depends(get_api_key)])
async def get_customer_360(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    months: int = Query(12, ge=1, le=36, description="Months of history to include")
):
    """
    🎯 Get complete 360° view of a customer/party
    
    Aggregates data from: ledgers, vouchers, bills, payments, inventory
    Returns everything needed for a Salesforce-style customer profile.
    """
    
    # 1. Get Basic Customer Info (Ledger)
    ledger = db.query(Ledger).filter(
        Ledger.id == customer_id,
        Ledger.tenant_id == tenant_id
    ).first()
    
    if not ledger:
        # Try finding by name as fallback
        ledger = db.query(Ledger).filter(
            Ledger.name == str(customer_id),
            Ledger.tenant_id == tenant_id
        ).first()
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_data = {
        "id": ledger.id,
        "name": ledger.name,
        "alias": ledger.alias,
        "group": ledger.parent,
        "ledger_type": ledger.ledger_type,
        "gstin": ledger.gstin,
        "pan": ledger.pan,
        "phone": ledger.phone,
        "email": ledger.email,
        "address": ledger.address,
        "city": ledger.city,
        "state": ledger.state,
        "pincode": ledger.pincode,
        "contact_person": ledger.contact_person,
        "opening_balance": ledger.opening_balance or 0.0,
        "closing_balance": ledger.closing_balance or 0.0,
        "balance_type": ledger.balance_type,
        "credit_limit": ledger.credit_limit,
        "credit_days": ledger.credit_days,
        "gst_registration_type": ledger.gst_registration_type,
        "created_at": ledger.created_at.isoformat() if ledger.created_at else None,
        "last_synced": ledger.last_synced.isoformat() if ledger.last_synced else None,
    }
    
    # Date range for queries
    start_date = datetime.now() - timedelta(days=months * 30)
    
    # 2. Transaction Summary
    transaction_summary = get_transaction_summary(db, ledger.name, tenant_id, start_date)
    
    # 3. Outstanding Bills
    outstanding_bills = get_outstanding_bills(db, ledger.name, tenant_id)
    
    # 4. Payment History (Last 10)
    recent_payments = get_recent_payments(db, ledger.name, tenant_id, limit=10)
    
    # 5. Recent Transactions (Last 20)
    recent_transactions = get_recent_transactions(db, ledger.name, tenant_id, limit=20)
    
    # 6. Top Items Purchased/Sold
    top_items = get_top_items(db, ledger.id, ledger.name, tenant_id, limit=10)
    
    # 7. Monthly Trend
    monthly_trend = get_monthly_trend(db, ledger.name, tenant_id, months=12)
    
    # 8. Calculate Insights
    insights = calculate_customer_insights(
        customer_data,
        transaction_summary,
        outstanding_bills,
        recent_payments,
        monthly_trend
    )
    
    # Build Summary with computed values
    summary = {
        **transaction_summary,
        "outstanding_total": sum(b.get('pending_amount', b.get('amount', 0)) for b in outstanding_bills),
        "overdue_total": sum(
            b.get('pending_amount', b.get('amount', 0)) 
            for b in outstanding_bills 
            if b.get('overdue_days', 0) > 0
        ),
        "outstanding_count": len(outstanding_bills),
        "overdue_count": sum(1 for b in outstanding_bills if b.get('overdue_days', 0) > 0),
        "credit_days_avg": insights.get('avg_credit_days', 0),
        "payment_promptness": insights.get('payment_score', 100),
        "current_balance": ledger.closing_balance or 0.0,
        "credit_limit": ledger.credit_limit,
        "credit_utilized_pct": round(
            (abs(ledger.closing_balance or 0) / ledger.credit_limit * 100) 
            if ledger.credit_limit and ledger.credit_limit > 0 else 0, 1
        )
    }
    
    return {
        "customer": customer_data,
        "summary": summary,
        "outstanding_bills": outstanding_bills,
        "recent_payments": recent_payments,
        "recent_transactions": recent_transactions,
        "top_items": top_items,
        "monthly_trend": monthly_trend,
        "insights": insights,
        "health_score": insights.get('health_score', 100)
    }


# --- Helper Functions ---

def get_transaction_summary(db: Session, party_name: str, tenant_id: str, start_date: datetime) -> Dict:
    """Get aggregated transaction statistics"""
    
    vouchers = db.query(Voucher).filter(
        Voucher.party_name == party_name,
        Voucher.tenant_id == tenant_id,
        Voucher.date >= start_date
    ).all()
    
    summary = {
        "transaction_count": len(vouchers),
        "total_sales": 0.0,
        "total_receipts": 0.0,
        "total_purchases": 0.0,
        "total_payments": 0.0,
        "first_transaction_date": None,
        "last_transaction_date": None
    }
    
    dates = []
    for v in vouchers:
        amt = v.amount or 0.0
        v_type = (v.voucher_type or "").lower()
        
        if "sales" in v_type:
            summary["total_sales"] += amt
        elif "receipt" in v_type:
            summary["total_receipts"] += amt
        elif "purchase" in v_type:
            summary["total_purchases"] += amt
        elif "payment" in v_type:
            summary["total_payments"] += amt
        
        if v.date:
            dates.append(v.date)
    
    if dates:
        summary["first_transaction_date"] = min(dates).strftime("%Y-%m-%d")
        summary["last_transaction_date"] = max(dates).strftime("%Y-%m-%d")
    
    return summary


def get_outstanding_bills(db: Session, party_name: str, tenant_id: str) -> List[Dict]:
    """Get unpaid bills with aging info"""
    
    bills = db.query(Bill).filter(
        Bill.party_name == party_name,
        Bill.tenant_id == tenant_id,
        Bill.amount > 0  # Outstanding
    ).order_by(Bill.due_date.asc()).all()
    
    today = datetime.now()
    result = []
    
    for bill in bills:
        overdue_days = 0
        if bill.due_date:
            overdue_days = (today - bill.due_date).days
            if overdue_days < 0:
                overdue_days = 0
        
        result.append({
            "bill_name": bill.bill_name,
            "amount": bill.amount,
            "pending_amount": bill.amount,  # Could track partial payments
            "due_date": bill.due_date.strftime("%Y-%m-%d") if bill.due_date else None,
            "overdue_days": overdue_days,
            "is_overdue": bill.is_overdue or overdue_days > 0,
            "aging_bucket": get_aging_bucket(overdue_days)
        })
    
    return result


def get_aging_bucket(days: int) -> str:
    """Categorize overdue days into aging buckets"""
    if days <= 0:
        return "current"
    elif days <= 30:
        return "1-30 days"
    elif days <= 60:
        return "31-60 days"
    elif days <= 90:
        return "61-90 days"
    else:
        return "90+ days"


def get_recent_payments(db: Session, party_name: str, tenant_id: str, limit: int = 10) -> List[Dict]:
    """Get recent receipt vouchers"""
    
    receipts = db.query(Voucher).filter(
        Voucher.party_name == party_name,
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%receipt%")
    ).order_by(Voucher.date.desc()).limit(limit).all()
    
    return [
        {
            "id": v.id,
            "date": v.date.strftime("%Y-%m-%d") if v.date else None,
            "voucher_number": v.voucher_number,
            "amount": v.amount,
            "narration": v.narration
        }
        for v in receipts
    ]


def get_recent_transactions(db: Session, party_name: str, tenant_id: str, limit: int = 20) -> List[Dict]:
    """Get recent vouchers of all types"""
    
    vouchers = db.query(Voucher).filter(
        Voucher.party_name == party_name,
        Voucher.tenant_id == tenant_id
    ).order_by(Voucher.date.desc()).limit(limit).all()
    
    return [
        {
            "id": v.id,
            "date": v.date.strftime("%Y-%m-%d") if v.date else None,
            "voucher_number": v.voucher_number,
            "voucher_type": v.voucher_type,
            "amount": v.amount,
            "narration": v.narration,
            "status": v.status
        }
        for v in vouchers
    ]


def get_top_items(db: Session, ledger_id: int, party_name: str, tenant_id: str, limit: int = 10) -> List[Dict]:
    """Get most transacted items with this customer"""
    
    # Join StockMovement -> StockItem -> Voucher where voucher.party_name matches
    results = db.query(
        StockItem.name,
        func.sum(StockMovement.quantity).label("total_qty"),
        func.sum(StockMovement.amount).label("total_amount"),
        func.count(func.distinct(Voucher.id)).label("txn_count"),
        func.avg(StockMovement.rate).label("avg_rate"),
        func.max(Voucher.date).label("last_date")
    ).join(
        StockMovement, StockMovement.item_id == StockItem.id
    ).join(
        Voucher, Voucher.id == StockMovement.voucher_id
    ).filter(
        Voucher.party_name == party_name,
        Voucher.tenant_id == tenant_id
    ).group_by(
        StockItem.name
    ).order_by(
        desc("total_amount")
    ).limit(limit).all()
    
    return [
        {
            "item_name": r.name,
            "total_quantity": r.total_qty or 0,
            "total_value": r.total_amount or 0,
            "transaction_count": r.txn_count or 0,
            "avg_rate": round(r.avg_rate or 0, 2),
            "last_date": r.last_date.strftime("%Y-%m-%d") if r.last_date else None
        }
        for r in results
    ]


def get_monthly_trend(db: Session, party_name: str, tenant_id: str, months: int = 12) -> List[Dict]:
    """Get monthly transaction trend"""
    
    start_date = datetime.now() - timedelta(days=months * 30)
    
    vouchers = db.query(Voucher).filter(
        Voucher.party_name == party_name,
        Voucher.tenant_id == tenant_id,
        Voucher.date >= start_date
    ).order_by(Voucher.date.asc()).all()
    
    # Aggregate by month
    monthly_data = {}
    for v in vouchers:
        if not v.date:
            continue
        month_key = v.date.strftime("%Y-%m")
        if month_key not in monthly_data:
            monthly_data[month_key] = {"sales": 0, "receipts": 0, "purchases": 0, "payments": 0}
        
        amt = v.amount or 0
        v_type = (v.voucher_type or "").lower()
        
        if "sales" in v_type:
            monthly_data[month_key]["sales"] += amt
        elif "receipt" in v_type:
            monthly_data[month_key]["receipts"] += amt
        elif "purchase" in v_type:
            monthly_data[month_key]["purchases"] += amt
        elif "payment" in v_type:
            monthly_data[month_key]["payments"] += amt
    
    # Convert to list and add display labels
    result = []
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        try:
            dt = datetime.strptime(month_key, "%Y-%m")
            label = dt.strftime("%b %Y")
        except:
            label = month_key
        
        result.append({
            "month": month_key,
            "label": label,
            "sales": data["sales"],
            "receipts": data["receipts"],
            "purchases": data["purchases"],
            "payments": data["payments"],
            "net": data["sales"] - data["receipts"] + data["purchases"] - data["payments"]
        })
    
    return result


def calculate_customer_insights(
    customer: Dict, 
    txn_summary: Dict, 
    bills: List[Dict], 
    payments: List[Dict],
    monthly_trend: List[Dict]
) -> Dict:
    """
    Calculate business intelligence metrics for customer health
    """
    insights = {
        "avg_credit_days": 0,
        "payment_score": 100,
        "health_score": 100,
        "risk_level": "low",
        "customer_tier": "bronze",
        "trend": "stable",
        "recommendations": []
    }
    
    # 1. Average Credit Days (from credit_days setting or calculate from payments)
    if customer.get("credit_days"):
        insights["avg_credit_days"] = customer["credit_days"]
    elif payments:
        # Could calculate from payment patterns vs invoice dates
        insights["avg_credit_days"] = 30  # Default estimate
    
    # 2. Payment Promptness Score (0-100)
    if bills:
        overdue_count = sum(1 for b in bills if b.get("overdue_days", 0) > 0)
        total_bills = len(bills)
        if total_bills > 0:
            promptness = ((total_bills - overdue_count) / total_bills) * 100
            insights["payment_score"] = round(promptness)
    
    # 3. Customer Tier (based on total sales)
    total_sales = txn_summary.get("total_sales", 0)
    if total_sales >= 1000000:  # 10 Lakh+
        insights["customer_tier"] = "platinum"
    elif total_sales >= 500000:  # 5 Lakh+
        insights["customer_tier"] = "gold"
    elif total_sales >= 100000:  # 1 Lakh+
        insights["customer_tier"] = "silver"
    else:
        insights["customer_tier"] = "bronze"
    
    # 4. Trend Analysis
    if len(monthly_trend) >= 3:
        recent_3 = monthly_trend[-3:]
        older_3 = monthly_trend[-6:-3] if len(monthly_trend) >= 6 else []
        
        recent_avg = sum(m.get("sales", 0) for m in recent_3) / 3
        
        if older_3:
            older_avg = sum(m.get("sales", 0) for m in older_3) / 3
            if recent_avg > older_avg * 1.1:
                insights["trend"] = "growing"
            elif recent_avg < older_avg * 0.9:
                insights["trend"] = "declining"
    
    # 5. Overall Health Score
    health = 100
    
    # Deductions
    closing_balance = customer.get("closing_balance", 0)
    credit_limit = customer.get("credit_limit")
    
    # Large outstanding balance
    if closing_balance > 100000:
        health -= 10
    if closing_balance > 500000:
        health -= 20
    
    # Credit limit breach
    if credit_limit and credit_limit > 0 and closing_balance > credit_limit:
        health -= 30
        insights["recommendations"].append("Credit limit exceeded - consider collection action")
    
    # Poor payment history
    if insights["payment_score"] < 70:
        health -= 20
        insights["recommendations"].append("Frequent late payments - review credit terms")
    elif insights["payment_score"] < 50:
        health -= 30
        insights["recommendations"].append("High default risk - consider cash-only terms")
    
    # Overdue bills
    overdue_amount = sum(b.get("pending_amount", b.get("amount", 0)) for b in bills if b.get("overdue_days", 0) > 0)
    if overdue_amount > 50000:
        health -= 15
        insights["recommendations"].append(f"Outstanding overdue: ₹{overdue_amount:,.0f}")
    
    # Declining trend
    if insights["trend"] == "declining":
        health -= 10
        insights["recommendations"].append("Business declining - consider loyalty incentives")
    
    # Growing relationship bonus
    if insights["trend"] == "growing":
        health += 10
    
    # Platinum customer bonus
    if insights["customer_tier"] == "platinum":
        health += 10
    
    insights["health_score"] = max(0, min(100, health))
    
    # 6. Risk Level
    if health >= 80:
        insights["risk_level"] = "low"
    elif health >= 60:
        insights["risk_level"] = "medium"
    else:
        insights["risk_level"] = "high"
    
    # Add positive recommendations
    if not insights["recommendations"]:
        if insights["customer_tier"] in ["platinum", "gold"]:
            insights["recommendations"].append("VIP customer - maintain excellent service")
        else:
            insights["recommendations"].append("Good standing customer")
    
    return insights


# --- Additional Utility Endpoints ---

@router.get("/search", dependencies=[Depends(get_api_key)])
async def search_customers(
    q: str = Query(..., min_length=1, description="Search query"),
    ledger_type: Optional[str] = Query(None, description="customer, supplier, or all"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Search customers/parties by name, phone, GSTIN, or email
    """
    query = db.query(Ledger).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.is_active == True,
        or_(
            Ledger.name.ilike(f"%{q}%"),
            Ledger.alias.ilike(f"%{q}%"),
            Ledger.phone.ilike(f"%{q}%"),
            Ledger.gstin.ilike(f"%{q}%"),
            Ledger.email.ilike(f"%{q}%")
        )
    )
    
    if ledger_type and ledger_type != "all":
        query = query.filter(Ledger.ledger_type == ledger_type)
    
    # Prioritize Sundry Debtors/Creditors (actual customers/suppliers)
    ledgers = query.order_by(
        case(
            (Ledger.parent.ilike("%debtor%"), 1),
            (Ledger.parent.ilike("%creditor%"), 2),
            else_=3
        ),
        Ledger.name
    ).limit(limit).all()
    
    return {
        "query": q,
        "count": len(ledgers),
        "customers": [
            {
                "id": l.id,
                "name": l.name,
                "alias": l.alias,
                "group": l.parent,
                "type": l.ledger_type,
                "phone": l.phone,
                "email": l.email,
                "gstin": l.gstin,
                "balance": l.closing_balance
            }
            for l in ledgers
        ]
    }


@router.get("/top", dependencies=[Depends(get_api_key)])
async def get_top_customers(
    by: str = Query("sales", description="Rank by: sales, balance, transactions"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get top customers ranked by sales, balance, or transaction count
    """
    # Get ledgers that are Sundry Debtors (customers)
    base_query = db.query(Ledger).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.is_active == True,
        Ledger.parent.ilike("%debtor%")
    )
    
    if by == "balance":
        # Top by outstanding balance
        ledgers = base_query.order_by(Ledger.closing_balance.desc()).limit(limit).all()
        
        return {
            "ranked_by": "balance",
            "customers": [
                {
                    "id": l.id,
                    "name": l.name,
                    "balance": l.closing_balance,
                    "phone": l.phone
                }
                for l in ledgers
            ]
        }
    
    elif by == "transactions":
        # Top by transaction count
        results = db.query(
            Ledger.id,
            Ledger.name,
            Ledger.closing_balance,
            Ledger.phone,
            func.count(Voucher.id).label("txn_count")
        ).join(
            Voucher, Voucher.party_name == Ledger.name
        ).filter(
            Ledger.tenant_id == tenant_id,
            Ledger.parent.ilike("%debtor%")
        ).group_by(
            Ledger.id
        ).order_by(
            desc("txn_count")
        ).limit(limit).all()
        
        return {
            "ranked_by": "transactions",
            "customers": [
                {
                    "id": r.id,
                    "name": r.name,
                    "balance": r.closing_balance,
                    "phone": r.phone,
                    "transaction_count": r.txn_count
                }
                for r in results
            ]
        }
    
    else:  # by == "sales"
        # Top by total sales
        results = db.query(
            Ledger.id,
            Ledger.name,
            Ledger.closing_balance,
            Ledger.phone,
            func.sum(Voucher.amount).label("total_sales")
        ).join(
            Voucher, Voucher.party_name == Ledger.name
        ).filter(
            Ledger.tenant_id == tenant_id,
            Ledger.parent.ilike("%debtor%"),
            Voucher.voucher_type.ilike("%sales%")
        ).group_by(
            Ledger.id
        ).order_by(
            desc("total_sales")
        ).limit(limit).all()
        
        return {
            "ranked_by": "sales",
            "customers": [
                {
                    "id": r.id,
                    "name": r.name,
                    "balance": r.closing_balance,
                    "phone": r.phone,
                    "total_sales": r.total_sales or 0
                }
                for r in results
            ]
        }


@router.get("/{customer_id}/aging", dependencies=[Depends(get_api_key)])
async def get_customer_aging(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get aging analysis for a specific customer's outstanding bills
    """
    ledger = db.query(Ledger).filter(
        Ledger.id == customer_id,
        Ledger.tenant_id == tenant_id
    ).first()
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    bills = get_outstanding_bills(db, ledger.name, tenant_id)
    
    # Bucket the amounts
    buckets = {
        "current": 0,
        "1-30 days": 0,
        "31-60 days": 0,
        "61-90 days": 0,
        "90+ days": 0
    }
    
    for bill in bills:
        bucket = bill.get("aging_bucket", "current")
        amount = bill.get("pending_amount", bill.get("amount", 0))
        if bucket in buckets:
            buckets[bucket] += amount
    
    total = sum(buckets.values())
    
    return {
        "customer_id": customer_id,
        "customer_name": ledger.name,
        "total_outstanding": total,
        "aging_buckets": buckets,
        "aging_summary": [
            {"bucket": k, "amount": v, "percentage": round(v/total*100, 1) if total > 0 else 0}
            for k, v in buckets.items()
        ],
        "bills": bills
    }
