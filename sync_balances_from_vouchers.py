"""
Calculate and update ledger balances from Vouchers table.
This uses the already-synced voucher data to compute current balances.
"""
import sys
sys.path.insert(0, '.')

from backend.database import get_db, Voucher, Ledger
from collections import defaultdict
from datetime import datetime

def calculate_balances_from_vouchers():
    """Calculate party balances from voucher transactions."""
    
    db = next(get_db())
    
    vouchers = db.query(Voucher).all()
    print(f"Total vouchers in DB: {len(vouchers)}")
    
    # Calculate balances from vouchers
    # For Sundry Creditors (suppliers):
    #   Purchase -> Credit to them (we owe them more)
    #   Payment -> Debit to them (we paid off debt)
    # For Sundry Debtors (customers):
    #   Sale -> Debit to them (they owe us more)
    #   Receipt -> Credit to them (they paid debt)
    
    party_balances = defaultdict(float)
    
    # Count by type
    type_counts = defaultdict(int)
    
    for v in vouchers:
        if not v.party_name:
            continue
        
        vtype = (v.voucher_type or '').lower()
        type_counts[v.voucher_type] += 1
        
        if 'purchase' in vtype or 'purc' in vtype:
            # Purchase from supplier - we owe them (Cr balance for them)
            party_balances[v.party_name] += v.amount
        elif 'sale' in vtype:
            # Sale to customer - they owe us (Dr balance for them)
            party_balances[v.party_name] += v.amount
        elif 'payment' in vtype:
            # Payment to supplier - reduce our debt (Dr to them)
            party_balances[v.party_name] -= v.amount
        elif 'receipt' in vtype:
            # Receipt from customer - reduce their debt (Cr to them)
            party_balances[v.party_name] -= v.amount
    
    print("\nVoucher Types:")
    for vtype, count in type_counts.items():
        print(f"  {vtype}: {count}")
    
    return party_balances


def update_ledger_balances(party_balances):
    """Update ledger table with calculated balances."""
    
    db = next(get_db())
    
    print("\n" + "=" * 60)
    print("CALCULATED PARTY BALANCES:")
    print("=" * 60)
    
    for party, bal in sorted(party_balances.items(), key=lambda x: abs(x[1]), reverse=True):
        if abs(bal) > 0:
            status = "Cr" if bal > 0 else "Dr"
            print(f"  {party}: Rs.{abs(bal):,.2f} {status}")
    
    # Update database
    updated = 0
    for party, bal in party_balances.items():
        ledger = db.query(Ledger).filter(Ledger.name == party).first()
        if ledger:
            ledger.closing_balance = bal
            ledger.last_synced = datetime.now()
            updated += 1
    
    db.commit()
    print(f"\nUpdated {updated} ledgers")
    
    # Show summary
    print("\n" + "=" * 60)
    print("SUNDRY DEBTORS (CUSTOMERS) - RECEIVABLES:")
    print("=" * 60)
    total_recv = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        bal = ld.closing_balance
        # Positive = they owe us (receivable)
        status = "Cr" if bal > 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(bal):,.2f} {status}")
        if bal > 0:
            total_recv += bal
    print(f"\n  TOTAL RECEIVABLES: Rs.{total_recv:,.2f}")
    
    print("\n" + "=" * 60)
    print("SUNDRY CREDITORS (SUPPLIERS) - PAYABLES:")
    print("=" * 60)
    total_pay = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        bal = ld.closing_balance
        # Positive = we owe them (payable)
        status = "Cr" if bal > 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(bal):,.2f} {status}")
        if bal > 0:
            total_pay += bal
    print(f"\n  TOTAL PAYABLES: Rs.{total_pay:,.2f}")
    
    return {
        'total_receivables': total_recv,
        'total_payables': total_pay
    }


if __name__ == "__main__":
    print("=" * 60)
    print("LEDGER BALANCE SYNC FROM VOUCHERS")
    print("=" * 60)
    
    balances = calculate_balances_from_vouchers()
    totals = update_ledger_balances(balances)
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    print(f"  Total Receivables: Rs.{totals['total_receivables']:,.2f}")
    print(f"  Total Payables: Rs.{totals['total_payables']:,.2f}")
