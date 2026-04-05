import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.sync_engine import SyncEngine
from backend.tally_live_update import PushResult, TallyResponse

class TestSyncEngine(unittest.TestCase):
    
    def setUp(self):
        self.engine = SyncEngine()
        # Mock the tally connector
        self.engine.tally = MagicMock()
        self.engine.tally.company_name = "Test Company"

    @patch("backend.sync_engine.create_voucher_in_tally")
    @patch("backend.sync_engine.create_ledger_safely")
    def test_push_voucher_safe_success(self, mock_create_ledger, mock_create_voucher):
        # Setup mocks
        mock_create_voucher.return_value = TallyResponse(
            raw_xml="<RESPONSE>OK</RESPONSE>",
            success=True,
            tally_status="Success",
            tally_response={"created": 1}
        )
        
        import uuid
        voucher_data = {
            "voucher_number": f"V001-{uuid.uuid4().hex[:8]}",
            "date": "20240401",
            "voucher_type": "Sales",
            "party_name": "Customer A",
            "amount": 1000,
            "narration": "Test"
        }
        
        # Execute
        result = self.engine.push_voucher_safe(voucher_data)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Voucher posted to Tally and saved locally.")
        
        # Verify ledger creation was attempted
        mock_create_ledger.assert_called()
        
        # Verify push was called
        mock_create_voucher.assert_called()

    @patch("backend.sync_engine.create_voucher_in_tally")
    @patch("backend.sync_engine.create_ledger_safely")
    def test_push_voucher_safe_tally_rejection(self, mock_create_ledger, mock_create_voucher):
        # Setup mock to simulate Tally rejection
        mock_create_voucher.return_value = TallyResponse(
            raw_xml="<RESPONSE>Error</RESPONSE>",
            success=False,
            tally_status="Failure",
            error_details="Invalid Date"
        )
        
        import uuid
        voucher_data = {
            "voucher_number": f"V002-{uuid.uuid4().hex[:8]}",
            "date": "20240401",
            "voucher_type": "Sales",
            "party_name": "Customer B",
            "amount": 500
        }
        
        result = self.engine.push_voucher_safe(voucher_data)
        
        self.assertFalse(result["success"])
        self.assertIn("Tally Rejected", result["error"])

    @patch("backend.sync_engine.create_voucher_in_tally")
    @patch("backend.sync_engine.create_ledger_safely")
    def test_push_voucher_safe_offline_mode(self, mock_create_ledger, mock_create_voucher):
        # Setup mock to raise exception (Network Error)
        import requests
        mock_create_voucher.side_effect = requests.ConnectionError("Connection failed")
        
        import uuid
        voucher_data = {
            "voucher_number": f"V003-{uuid.uuid4().hex[:8]}",
            "date": "20240401",
            "voucher_type": "Sales",
            "party_name": "Customer C",
            "amount": 200
        }
        
        result = self.engine.push_voucher_safe(voucher_data)
        
        self.assertTrue(result["success"])
        self.assertIn("Tally is offline", result["message"])
        self.assertEqual(result["warning"], "Offline Mode")

if __name__ == '__main__':
    unittest.main()
