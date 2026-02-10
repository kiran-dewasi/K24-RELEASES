from backend.tally_search import TallySearch
import logging
import sys

# Configure stdout logging to see raw output
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("\n--- FORCED CACHE WARMUP ---")
    search = TallySearch(tally_url="http://localhost:9000")
    # ENABLE DEBUG XML
    search.reader.debug_xml = True
    
    # 1. Ledgers
    print("\n[Step 1] Refreshing Ledgers...")
    # Force clear internal cache to trigger refresh
    search._ledger_cache = [] 
    ledger_result = search.smart_ledger_search("Prince Ent")
    
    print(f"\n[DEBUG] Found {len(search._ledger_cache)} Ledgers:")
    print(search._ledger_cache)

    # 2. Items
    print("\n[Step 2] Refreshing Items...")
    search._item_cache = []
    item_result = search.smart_item_search("Jeera")
    
    print("\n--- DONE ---")
