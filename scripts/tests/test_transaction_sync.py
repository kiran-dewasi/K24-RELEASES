import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.sync_engine import SyncEngine
from backend.database import SessionLocal, Voucher

class TestTransactionSync(unittest.TestCase):
    def setUp(self):
        self.sync_engine = SyncEngine()
        self.db = SessionLocal()
        # Clean up test vouchers
        self.db.query(Voucher).filter(Voucher.narration == "TEST_SYNC_TX").delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(Voucher).filter(Voucher.narration == "TEST_SYNC_TX").delete()
        self.db.commit()
        self.db.close()

    @patch('backend.tally_connector.TallyConnector.create_voucher')
    def test_push_voucher_safe_success(self, mock_create):
        # Simulate Tally Success
        mock_create.return_value = {
            "success": True,
            "status": "Success",
            "created": 1,
            "errors": []
        }

        voucher_data = {
            "voucher_type": "Sales",
            "party_name": "Test Party",
            "amount": 1000,
            "narration": "TEST_SYNC_TX",
            "date": "20241101"
        }

        result = self.sync_engine.push_voucher_safe(voucher_data)
        
        # Verify Result
        self.assertTrue(result["success"])
        
        # Verify DB Commit
        saved_voucher = self.db.query(Voucher).filter(Voucher.narration == "TEST_SYNC_TX").first()
        self.assertIsNotNone(saved_voucher)
        self.assertEqual(saved_voucher.amount, 1000)

    @patch('backend.tally_connector.TallyConnector.create_voucher')
    def test_push_voucher_safe_failure(self, mock_create):
        # Simulate Tally Failure
        mock_create.return_value = {
            "success": False,
            "status": "Failure",
            "created": 0,
            "errors": ["Invalid Date for Edu Mode"]
        }

        voucher_data = {
            "voucher_type": "Sales",
            "party_name": "Test Party",
            "amount": 2000,
            "narration": "TEST_SYNC_TX",
            "date": "20241122" # Invalid for Edu Mode
        }

        result = self.sync_engine.push_voucher_safe(voucher_data)
        
        # Verify Result
        self.assertFalse(result["success"])
        self.assertIn("Tally Rejected", result["error"])
        
        # Verify NO DB Commit (Rollback)
        saved_voucher = self.db.query(Voucher).filter(Voucher.narration == "TEST_SYNC_TX").first()
        self.assertIsNone(saved_voucher)

if __name__ == '__main__':
    unittest.main()
