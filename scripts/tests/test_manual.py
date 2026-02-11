from backend.tally_connector import TallyConnector

tally = TallyConnector()

# Try to create Cash ledger
print("Creating Cash ledger...")
result = tally.create_ledger_if_missing("Cash", "Cash-in-Hand")
print(f"Result: {result}")

# Try to create a test customer
print("\nCreating Test Customer...")
result2 = tally.create_ledger_if_missing("TestCustomer999", "Sundry Debtors")
print(f"Result: {result2}")

# Now try to create a receipt
print("\nCreating Receipt voucher...")
from datetime import datetime
voucher_data = {
    "voucher_type": "Receipt",
    "date": datetime.now().strftime("%Y%m01"),
    "party_name": "TestCustomer999",
    "amount": 1000.0,
    "narration": "Manual test receipt",
    "deposit_to": "Cash"
}
result3 = tally.create_voucher(voucher_data)
print(f"Result: {result3}")
