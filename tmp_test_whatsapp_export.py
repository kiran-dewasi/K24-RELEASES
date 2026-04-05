import sys
import os
import traceback
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from services.export_service import export_sales_to_excel

def test_whatsapp_adapter():
    try:
        print("Testing export_sales_to_excel via WhatsApp adapter...")
        
        # Real-looking dates
        date_from = datetime.strptime("2024-04-01", "%Y-%m-%d")
        date_to = datetime.strptime("2025-03-31", "%Y-%m-%d")
        
        res = export_sales_to_excel(date_from=date_from, date_to=date_to)
        print(f"Result: {res}")
        
        assert res.get("success") is True, "Success should be True"
        assert "file_path" in res and res["file_path"], "file_path should be non-empty string"
        
        file_path = res["file_path"]
        assert os.path.exists(file_path), "File does not exist on disk"
        
        size = os.path.getsize(file_path)
        print(f"File size: {size} bytes")
        assert size > 500, "File size should be > 500 bytes"
        
        filename = res.get("filename", "")
        assert filename.endswith(".xlsx"), "Filename should end with .xlsx"
        
        print("TEST PASSED!")
    except Exception as e:
        print("TEST FAILED!")
        traceback.print_exc()

if __name__ == "__main__":
    test_whatsapp_adapter()
