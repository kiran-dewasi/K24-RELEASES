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
            status="Success",
            created=1
        )
        
        voucher_data = {
            "voucher_number": "V001",
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
    def test_push_voucher_safe_tally_rejection(self, mock_create_voucher):
        # Setup mock to simulate Tally rejection
        mock_create_voucher.return_value = TallyResponse(
            raw_xml="<RESPONSE>Error</RESPONSE>",
            status="Failure",
            errors=["Invalid Date"]
        )
        
        voucher_data = {
            "voucher_number": "V002",
            "date": "20240401",
            "voucher_type": "Sales",
            "party_name": "Customer B",
            "amount": 500
        }
        
        result = self.engine.push_voucher_safe(voucher_data)
        
        self.assertFalse(result["success"])
        self.assertIn("Tally Rejected", result["error"])

    @patch("backend.sync_engine.create_voucher_in_tally")
    def test_push_voucher_safe_offline_mode(self, mock_create_voucher):
        # Setup mock to raise exception (Network Error)
        import requests
        mock_create_voucher.side_effect = requests.ConnectionError("Connection failed")
        
        voucher_data = {
            "voucher_number": "V003",
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
