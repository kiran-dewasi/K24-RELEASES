"""
Quick script to check Shadow DB contents
"""
from backend.database import SessionLocal, Ledger, Voucher, Bill, StockItem

db = SessionLocal()

print("=" * 60)
print("K24 SHADOW DATABASE STATUS")
print("=" * 60)

# Count records
ledgers_count = db.query(Ledger).count()
vouchers_count = db.query(Voucher).count()
bills_count = db.query(Bill).count()
items_count = db.query(StockItem).count()

print(f"\n📊 Record Counts:")
print(f"  - Ledgers: {ledgers_count}")
print(f"  - Vouchers: {vouchers_count}")
print(f"  - Bills: {bills_count}")
print(f"  - Stock Items: {items_count}")

# Check receivables specifically
receivables = db.query(Bill).filter(Bill.amount > 0).all()
payables = db.query(Bill).filter(Bill.amount < 0).all()

print(f"\n💰 Bills Breakdown:")
print(f"  - Receivables (amount > 0): {len(receivables)}")
print(f"  - Payables (amount < 0): {len(payables)}")

if receivables:
    print(f"\n📋 Receivables Details:")
    for bill in receivables:
        print(f"  - {bill.bill_name}: {bill.party_name} - ₹{bill.amount:,.2f}")
else:
    print(f"\n❌ No receivables found in database!")
    print(f"\n💡 Possible reasons:")
    print(f"  1. No sales invoices created yet")
    print(f"  2. Data hasn't been synced from Tally")
    print(f"  3. All invoices have been fully paid")

# Check if there are any ledgers
if ledgers_count > 0:
    print(f"\n👥 Sample Ledgers:")
    for ledger in db.query(Ledger).limit(5).all():
        print(f"  - {ledger.name} (Balance: ₹{ledger.closing_balance:,.2f})")
        
# Check if there are any vouchers
if vouchers_count > 0:
    print(f"\n📝 Recent Vouchers:")
    for voucher in db.query(Voucher).order_by(Voucher.date.desc()).limit(5).all():
        print(f"  - {voucher.voucher_type}: {voucher.party_name} - ₹{voucher.amount:,.2f} ({voucher.sync_status})")

print("\n" + "=" * 60)
db.close()
