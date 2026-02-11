import json
import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db, UserSettings
from backend.database.encryption import encryptor

CONFIG_FILE = "k24_config.json"

def migrate_keys():
    print("Locked & Loading migration...")
    
    if not os.path.exists(CONFIG_FILE):
        print("Config file not found. Skipping.")
        return

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    api_key = config.get("google_api_key")
    
    if not api_key or len(api_key) < 10:
        print("No valid API key found in config.")
        return

    print(f"Found API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Encrypt
    encrypted_key = encryptor.encrypt(api_key)
    print("Encryption successful.")

    # Save to DB for default user (assumed user_id=1 or 'default')
    # Since we use tenant/user system, we need to know WHICH user.
    # We'll attach it to the first admin user found, or 'default' if none.
    
    try:
        db = next(get_db())
        
        # Try to find a user
        # user = db.query(User).first()
        # user_id = user.id if user else "1"
        user_id = "default_user" # As per chat endpoint default
        
        print(f"Migrating key to user: {user_id}")
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id, google_api_key=encrypted_key)
            db.add(settings)
        else:
            settings.google_api_key = encrypted_key
        
        db.commit()
        print("Key saved to database.")
        
        # Remove from config file
        del config["google_api_key"]
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
            
        print("❌ Removed API key from k24_config.json")
        print("✅ Migration Complete!")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_keys()
