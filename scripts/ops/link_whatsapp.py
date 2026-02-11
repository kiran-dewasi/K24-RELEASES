from backend.database import SessionLocal, Ledger, WhatsAppMapping, Tenant

def link_user():
    db = SessionLocal()
    try:
        phone = "917339906200"
        party_name = "Krisha Sales"
        
        # 1. Find or Create Ledger
        ledger = db.query(Ledger).filter(Ledger.name == party_name).first()
        if not ledger:
            print(f"❌ Ledger '{party_name}' not found. Creating placeholder...")
            # Create a placeholder ledger/tenant if needed for testing
            ledger = Ledger(
                name=party_name,
                tenant_id="TENANT-DEFAULT", # Assuming default tenant
                phone=phone
            )
            db.add(ledger)
            db.commit()
            db.refresh(ledger)
            print(f"✅ Created Ledger: {ledger.id}")
        else:
            print(f"✅ Found Ledger: {ledger.name} (ID: {ledger.id})")
            
        # 2. Link in WhatsAppMapping
        mapping = db.query(WhatsAppMapping).filter(WhatsAppMapping.whatsapp_number == phone).first()
        if not mapping:
            mapping = WhatsAppMapping(
                whatsapp_number=phone,
                contact_id=ledger.id,
                tenant_id=ledger.tenant_id
            )
            db.add(mapping)
            print(f"✅ Created Mapping: {phone} -> {party_name}")
        else:
            mapping.contact_id = ledger.id
            print(f"✅ Updated Mapping: {phone} -> {party_name}")
            
        db.commit()
        print("🎉 SUCCESS! You can now chat with the agent.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    link_user()
