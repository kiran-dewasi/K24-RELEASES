
from backend.database import SessionLocal, Ledger

def check_group():
    db = SessionLocal()
    name = "VINAYAK ENETRPRISES"
    ledger = db.query(Ledger).filter(Ledger.name == name).first()
    if ledger:
        print(f"Ledger: {ledger.name}")
        print(f"Parent: '{ledger.parent}'")
        print(f"Balance: {ledger.closing_balance}")
    else:
        print(f"Ledger {name} NOT FOUND")
        
    # Check what K PRA parent is
    kpra = db.query(Ledger).filter(Ledger.name == "K PRA FOODS PRIVATE LIMITED").first()
    if kpra:
        print(f"K PRA Parent: '{kpra.parent}'")

if __name__ == "__main__":
    check_group()
