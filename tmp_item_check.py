from backend.tally_reader import TallyReader
r = TallyReader()
r.fetch_all_items()
print("=== ALL ITEMS IN TALLY ===")
for k, v in sorted(r.item_cache.items()):
    print(f"  KEY=[{repr(k)}]  VALUE=[{repr(v)}]")

print()
result = r.check_item_exists("Jeera")
print(f"check_item_exists('Jeera') -> {repr(result)}")

result2 = r.check_item_exists("jeera")
print(f"check_item_exists('jeera') -> {repr(result2)}")

result3 = r.check_item_exists("Cumin Seeds")
print(f"check_item_exists('Cumin Seeds') -> {repr(result3)}")
