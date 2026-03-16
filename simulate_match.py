import re
import difflib

def simulate_matching():
    with open('ledgers_raw.xml', 'rb') as f:
        content = f.read()
    try:
        text = content.decode('utf-8')
    except:
        text = content.decode('utf-16')

    # Simple regex to get all ledger names
    ledger_names = re.findall(r'<LEDGER[^>]*NAME="([^"]+)"', text, re.I)
    
    # Also check <NAME>Text</NAME>
    ledger_names += re.findall(r'<LEDGER[^>]*>.*?<NAME>([^<]+)</NAME>', text, re.S | re.I)
    
    # Unique and normalized
    ledger_cache = {}
    for name in set(ledger_names):
        normalized = " ".join(name.split()).lower()
        ledger_cache[normalized] = name.strip()

    search_query = "Prince Enterprises"
    key = " ".join(search_query.split()).lower()
    
    print(f"Searching for: '{key}'")
    
    # 1. Exact match
    if key in ledger_cache:
        print(f"EXACT MATCH found: {ledger_cache[key]}")
        return

    # 2. Substring match
    for cached_key, cached_name in ledger_cache.items():
        if key in cached_key:
            print(f"SUBSTRING MATCH (Key in Cache): '{key}' in '{cached_key}' -> '{cached_name}'")
            return
        if cached_key in key and len(cached_key) > 3: # To avoid micro-matches
             print(f"SUBSTRING MATCH (Cache in Key): '{cached_key}' in '{key}' -> '{cached_name}'")
             # Wait, the actual code doesn't have the len(cached_key) > 3 check! 
             # Let's check the actual code again.
    
    # 3. Fuzzy match
    all_keys = list(ledger_cache.keys())
    close = difflib.get_close_matches(key, all_keys, n=1, cutoff=0.75)
    if close:
        print(f"FUZZY MATCH: '{key}' matches '{close[0]}' -> '{ledger_cache[close[0]]}'")
        return

    print("NO MATCH FOUND.")

if __name__ == "__main__":
    simulate_matching()
