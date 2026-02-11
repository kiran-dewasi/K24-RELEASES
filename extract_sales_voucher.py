
import re

with open('backend/voucher_dump.xml', 'r', encoding='utf-8') as f:
    content = f.read()

# Regex to find VCHTYPE="Sales" voucher block
# Vouchers are inside <TALLYMESSAGE>
# Structure: <TALLYMESSAGE ...> <VOUCHER ... VCHTYPE="Sales" ...> ... </VOUCHER> </TALLYMESSAGE>

pattern = re.compile(r'(<VOUCHER [^>]*VCHTYPE="Sales"[^>]*>.*?</VOUCHER>)', re.DOTALL)
match = pattern.search(content)

if match:
    with open('backend/sales_voucher.xml', 'w', encoding='utf-8') as out:
        out.write(match.group(1))
    print("Saved to backend/sales_voucher.xml")
else:
    print("Sales Voucher NOT FOUND")
