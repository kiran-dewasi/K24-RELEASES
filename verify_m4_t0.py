
import os
import sys
import logging
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

# Setup logging - suppress noise
logging.basicConfig(level=logging.CRITICAL)
# Also suppress lower level logs from imported modules
logging.getLogger("desktop.services").setLevel(logging.CRITICAL)
logging.getLogger("backend.services").setLevel(logging.CRITICAL)
logger = logging.getLogger("m4_t0_verifier")

def test_config_service():
    print("\n--- Testing Config Service ---")
    try:
        from backend.services.config_service import get_cloud_url, get_desktop_api_key, get_tenant_id
        
        url = get_cloud_url()
        print(f"Cloud URL: {url}")
        
        # Verify it matches cloud.json if no env var set
        config_path = Path("backend/config/cloud.json")
        if config_path.exists():
            with open(config_path, "r") as f:
                data = json.load(f)
                expected_url = data.get("cloud_api_url")
                if url == expected_url:
                    print("✅ Cloud URL matches config.json")
                else:
                    print(f"❌ Cloud URL mismatch! Expected {expected_url}, Got {url}")
        else:
            print("⚠️ config.json missing!")
            
    except ImportError as e:
        print(f"❌ Failed to import config_service: {e}")
    except Exception as e:
        print(f"❌ Config service test failed: {e}")

def test_token_storage():
    print("\n--- Testing Token Storage (Tenant Persistence) ---")
    try:
        from desktop.services.token_storage import save_tokens, get_stored_tenant_id, clear_tokens, get_token_storage
        
        storage = get_token_storage()
        
        # 1. Clear existing tokens (backup if needed? No, this is dev/test)
        # We'll use a test tenant ID so we don't clobber real dev data if possible?
        # Typically we shouldn't wipe real dev tokens.
        # Let's read current state first.
        original_context = storage.load_context()
        # print(f"Original Context: {original_context}") # details hidden since logging is critical
        print("Original context loaded.")
        
        # 2. Save new test tokens with tenant_id
        test_tenant = "test_tenant_123"
        test_user = "test_user_456"
        save_tokens("test_access", "test_refresh", tenant_id=test_tenant, user_id=test_user)
        
        # 3. Verify get_stored_tenant_id
        stored_tenant = get_stored_tenant_id()
        if stored_tenant == test_tenant:
            print(f"✅ Tenant ID persistence working: {stored_tenant}")
        else:
            print(f"❌ Tenant ID persistence failed! Expected {test_tenant}, Got {stored_tenant}")
            
        # 4. Verify context via instance method
        context = storage.load_context()
        if context.get("user_id") == test_user:
            print(f"✅ User ID persistence working: {context.get('user_id')}")
        else:
            print(f"❌ User ID persistence failed!")
            
        # 5. Cleanup/Restore
        # Restore original if it existed, else clear
        if original_context.get("access_token"):
            save_tokens(
                original_context["access_token"], 
                original_context["refresh_token"],
                tenant_id=original_context.get("tenant_id"),
                user_id=original_context.get("user_id")
            )
            print("✅ Original tokens restored")
        else:
            clear_tokens()
            print("✅ Test tokens cleared")
            
    except Exception as e:
        print(f"❌ Token storage test failed: {e}")
        import traceback
        traceback.print_exc()

def test_poller_init():
    print("\n--- Testing WhatsApp Poller Initialization ---")
    try:
        # Set env vars temporarily to simulate conditions if needed
        # But we want to test config_service integration
        # Poller needs tenant_id. We just set/restored it.
        # If we restored empty, poller init might fail (warning).
        
        from desktop.services.whatsapp_poller import init_poller
        
        # Mock tenant_id in storage for this test
        from desktop.services.token_storage import save_tokens, clear_tokens
        save_tokens("fake_access", "fake_refresh", tenant_id="poller_test_tenant")
        
        # Also needs API Key in env or config
        os.environ["DESKTOP_API_KEY"] = "test_api_key_123"
        
        poller = init_poller()
        
        if poller:
            print(f"✅ Poller initialized successfully")
            print(f"   Base URL: {poller.base_url}")
            print(f"   Tenant ID: {poller.tenant_id}")
            
            if poller.tenant_id == "poller_test_tenant":
                 print("✅ Poller picked up Tenant ID from TokenStorage")
            else:
                 print("❌ Poller failed to pick up correct Tenant ID")
        else:
            print("❌ Poller failed to initialize (check logs)")
            
        # Cleanup
        clear_tokens()
        del os.environ["DESKTOP_API_KEY"]
        
    except Exception as e:
        print(f"❌ Poller init test failed: {e}")

if __name__ == "__main__":
    test_config_service()
    test_token_storage()
    test_poller_init()
