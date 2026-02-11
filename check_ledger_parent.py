
from backend.database import SessionLocal, Ledger

def check():
    db = SessionLocal()
    ledgers = ["K PRA FOODS PRIVATE LIMITED", "SHIVALINGAPPA AND SONS", "SHREE GANESH TRADERS", "UTSAV FOODS"]
    for name in ledgers:
        l = db.query(Ledger).filter(Ledger.name == name).first()
        if l:
            print(f"Ledger: {l.name}, Parent: {l.parent}, Balance: {l.closing_balance}")
        else:
            print(f"Ledger: {name} NOT FOUND in DB")

if __name__ == "__main__":
    check()
