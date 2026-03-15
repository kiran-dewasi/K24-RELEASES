"""
CONFIRMED DIAGNOSTIC — no guessing
"""
import sys
sys.path.insert(0, '.')

from backend.tally_reader import TallyReader

r = TallyReader()
r.fetch_all_items()

print("=== EVERY ITEM IN TALLY RIGHT NOW ===")
for k, v in sorted(r.item_cache.items()):
    print(f"  KEY={repr(k):50s}  VALUE={repr(v)}")

print()
print(f"Total items: {len(r.item_cache)}")
print()

# Exact test of what check_item_exists returns
tests = ["Jeera", "jeera", "Cumin Seeds", "CUMIN SEEDS", "cumin seeds ( jeera )"]
for t in tests:
    result = r.check_item_exists(t)
    print(f"  check_item_exists({repr(t):30s}) → {repr(result)}")
