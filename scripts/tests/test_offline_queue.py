import pytest
from unittest.mock import MagicMock, patch
from backend.sync_engine import SyncEngine
from backend.database import Voucher, SessionLocal
from datetime import datetime
import requests

def test_offline_queue_logic():
    # Mock TallyConnector to raise an exception (simulate offline)
    with patch('backend.sync_engine.TallyConnector') as MockConnector:
        # Setup mock to raise RequestException on create_voucher
        mock_instance = MockConnector.return_value
        mock_instance.create_voucher.side_effect = requests.RequestException("Simulated Connection Error")
        
        engine = SyncEngine()
        
        # Test Data
        voucher_data = {
            "voucher_number": "TEST-OFFLINE-001",
            "date": "20240401",
            "voucher_type": "Sales",
            "party_name": "Test Party",
            "amount": 5000,
            "narration": "Testing Offline Queue"
        }
        
        # Execute Push
        print("Attempting push (expecting failure and offline save)...")
        result = engine.push_voucher_safe(voucher_data)
        
        # Verify Result
        print(f"Result: {result}")
        assert result['success'] == True
        assert "Tally is offline" in result['message']
        assert result['warning'] == "Offline Mode"
        
        # Verify DB
        db = SessionLocal()
        saved_voucher = db.query(Voucher).filter(Voucher.voucher_number == "TEST-OFFLINE-001").first()
        assert saved_voucher is not None
        assert saved_voucher.sync_status == "PENDING"
        print("✅ Voucher saved with status PENDING")
        
        # Cleanup
        db.delete(saved_voucher)
        db.commit()
        db.close()

if __name__ == "__main__":
    try:
        test_offline_queue_logic()
        print("✅ Offline Queue Test Passed!")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
