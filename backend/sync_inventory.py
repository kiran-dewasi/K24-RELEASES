from backend.database import SessionLocal, StockItem, InventoryEntry
from backend.tally_reader import TallyReader
import logging

logger = logging.getLogger("InventorySync")

def sync_tally_stock_items(tenant_id="TENANT-12345"):
    """
    Fetches all Stock Items from Tally and updates local DB.
    """
    try:
        reader = TallyReader()
        items = reader.get_stock_summary()
        
        if not items:
            print("No items fetched from Tally.")
            return

        db = SessionLocal()
        count = 0
        
        for item in items:
            name = item.get("name")
            if not name: continue
            
            # Check existing
            existing = db.query(StockItem).filter(StockItem.name == name).first() # Tenant filter later
            
            cost = 0.0
            price = 0.0
            
            # Parse Price info if available (Standard Cost/Price usually "120.00/kgs")
            if item.get("standard_cost"):
                 try: cost = float(item["standard_cost"].split('/')[0])
                 except: pass
            if item.get("standard_price"):
                 try: price = float(item["standard_price"].split('/')[0])
                 except: pass

            if not existing:
                new_item = StockItem(
                    tenant_id=tenant_id,
                    name=name,
                    parent=item.get("parent"),
                    units=item.get("units"),
                    opening_balance=item.get("opening_balance", 0.0),
                    closing_balance=item.get("closing_balance", 0.0),
                    cost_price=cost,
                    selling_price=price,
                    # HSN/GST currently not fetched in summary
                )
                db.add(new_item)
                print(f"➕ Created Item: {name}")
            else:
                # Update
                existing.closing_balance = item.get("closing_balance", 0.0)
                existing.opening_balance = item.get("opening_balance", 0.0)
                existing.units = item.get("units")
                existing.cost_price = cost
                existing.selling_price = price
                # print(f"🔄 Updated Item: {name}") # Too noisy
                
            count += 1
            
        db.commit()
        db.close()
        print(f"✅ Synced {count} Stock Items from Tally.")
        
    except Exception as e:
        print(f"❌ Inventory Sync Failed: {e}")

if __name__ == "__main__":
    sync_tally_stock_items()
