
with open('backend/voucher_dump.xml', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if '<VOUCHER ' in line:
            print(f"{i+1}: {line.strip()}")
