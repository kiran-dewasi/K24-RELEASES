
from backend.database import SessionLocal, Ledger

def check_kpra():
    db = SessionLocal()
    name = "K PRA FOODS PRIVATE LIMITED"
    ledger = db.query(Ledger).filter(Ledger.name == name).first()
    if ledger:
        print(f"Ledger: {ledger.name}")
        print(f"Balance: {ledger.closing_balance}")
    else:
        print(f"Ledger {name} NOT FOUND")

if __name__ == "__main__":
    check_kpra()
