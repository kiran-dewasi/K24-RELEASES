
def scan():
    with open("bills_receivable.xml", "r", encoding="utf-16") as f:
        content = f.read()
    if "K PRA" in content:
        print("FOUND K PRA")
    else:
        print("NOT FOUND")

if __name__ == "__main__":
    scan()
