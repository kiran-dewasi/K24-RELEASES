import unittest
from fastapi.testclient import TestClient
from backend.api import app
from backend.database import init_db, SessionLocal, Base, engine

class TestHeadlessAPI(unittest.TestCase):
    def setUp(self):
        # Reset DB
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def test_full_flow(self):
        # 1. Trigger Sync
        print("\nTesting Sync...")
        response = self.client.post("/sync")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], "Sync Started")
        
        # Note: TestClient runs background tasks synchronously, so DB should be populated now.
        
        # 2. Test Ledgers
        print("Testing /ledgers...")
        response = self.client.get("/ledgers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) >= 3)
        self.assertEqual(data[0]['name'], "Vasudev Enterprises")

        # 3. Test Items
        print("Testing /items...")
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) >= 3)
        self.assertEqual(data[0]['name'], "Dell Laptop")

        # 4. Test Receivables (The "Relief" Button)
        print("Testing /bills/receivables...")
        response = self.client.get("/bills/receivables")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # In sync_engine, Sharma (5000) and Vasudev (12000) are bills. 
        # Assuming positive amount is receivable.
        self.assertTrue(len(data) > 0)
        self.assertTrue(all(b['amount'] > 0 for b in data))

        # 5. Test Daybook (The "Pulse" Check)
        print("Testing /reports/daybook...")
        response = self.client.get("/reports/daybook")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) >= 2)
        self.assertEqual(data[0]['voucher_type'], "Sales")

        # 6. Test Search (The "God Mode")
        print("Testing /search...")
        # Search for "Sharma" (Should find Ledger and Bill and Voucher)
        response = self.client.get("/search?q=Sharma")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data['ledgers']) > 0)
        self.assertTrue(len(data['vouchers']) > 0)
        print("Search found:", data)

if __name__ == '__main__':
    unittest.main()
