import unittest
from decimal import Decimal
from backend.tally_xml_builder import (
    build_ledger_create_xml,
    build_voucher_create_xml,
    build_stock_item_create_xml,
    VoucherLineItem,
    TallyXMLValidationError
)

class TestTallyXMLBuilder(unittest.TestCase):
    
    def test_build_ledger_create_xml(self):
        xml = build_ledger_create_xml(
            "Test Company",
            "Test Ledger",
            {"PARENT": "Sundry Debtors", "OPENINGBALANCE": 1000}
        )
        self.assertIn('<LEDGER NAME="Test Ledger" ACTION="Create">', xml)
        self.assertIn('<PARENT>Sundry Debtors</PARENT>', xml)
        self.assertIn('<OPENINGBALANCE>1000</OPENINGBALANCE>', xml)
        self.assertIn('<SVCURRENTCOMPANY>Test Company</SVCURRENTCOMPANY>', xml)

    def test_build_stock_item_create_xml(self):
        xml = build_stock_item_create_xml(
            "Test Company",
            "Test Item",
            {"PARENT": "Hardware", "BASEUNITS": "Nos", "OPENINGBALANCE": 50}
        )
        self.assertIn('<STOCKITEM NAME="Test Item" ACTION="Create">', xml)
        self.assertIn('<PARENT>Hardware</PARENT>', xml)
        self.assertIn('<BASEUNITS>Nos</BASEUNITS>', xml)
        self.assertIn('<OPENINGBALANCE>50</OPENINGBALANCE>', xml)

    def test_build_voucher_create_xml(self):
        fields = {
            "DATE": "20240401",
            "VOUCHERTYPENAME": "Sales",
            "VOUCHERNUMBER": "INV-001",
            "PARTYLEDGERNAME": "Customer A",
            "NARRATION": "Test Sales"
        }
        line_items = [
            {"ledger_name": "Customer A", "amount": -1000, "is_deemed_positive": "Yes"},
            {"ledger_name": "Sales", "amount": 1000, "is_deemed_positive": "No"}
        ]
        xml = build_voucher_create_xml("Test Company", fields, line_items)
        
        self.assertIn('<VOUCHER VCHTYPE="Sales" ACTION="Create">', xml)
        self.assertIn('<DATE>20240401</DATE>', xml)
        self.assertIn('<VOUCHERNUMBER>INV-001</VOUCHERNUMBER>', xml)
        self.assertIn('<LEDGERNAME>Customer A</LEDGERNAME>', xml)
        self.assertIn('<AMOUNT>-1000</AMOUNT>', xml)
        self.assertIn('<LEDGERNAME>Sales</LEDGERNAME>', xml)
        self.assertIn('<AMOUNT>1000</AMOUNT>', xml)

    def test_validation_error(self):
        with self.assertRaises(TallyXMLValidationError):
            build_ledger_create_xml("", "Ledger", {}) # Missing company

if __name__ == '__main__':
    unittest.main()
