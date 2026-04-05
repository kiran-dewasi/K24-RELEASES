import unittest
from backend.tally_response_parser import parse_tally_response
from backend.tally_live_update import TallyResponse

class TestTallyResponseParser(unittest.TestCase):
    
    def test_parse_success(self):
        xml = """
        <RESPONSE>
            <CREATED>1</CREATED>
            <ALTERED>0</ALTERED>
            <DELETED>0</DELETED>
            <LASTVCHID>123</LASTVCHID>
            <GUID>guid-123</GUID>
            <STATUS>Success</STATUS>
        </RESPONSE>
        """
        response = parse_tally_response(xml)
        self.assertTrue(response.succeeded)
        self.assertEqual(response.tally_response.get("created"), 1)
        self.assertEqual(response.tally_status, "Success")
        self.assertEqual(response.error_details, "")

    def test_parse_failure_with_errors(self):
        xml = """
        <RESPONSE>
            <CREATED>0</CREATED>
            <ALTERED>0</ALTERED>
            <ERRORS>
                <ERROR>Invalid Date</ERROR>
                <LINEERROR>Missing Ledger</LINEERROR>
            </ERRORS>
            <STATUS>Failure</STATUS>
        </RESPONSE>
        """
        # Note: The parser logic in tally_live_update.py uses .//ERROR and .//LINEERROR
        # Let's verify if parse_tally_response in tally_live_update.py handles this structure.
        # It uses:
        # errors = []
        # for tag in ("LINEERROR", "ERROR"):
        #     for node in root.findall(f".//{tag}"): ...
        
        response = parse_tally_response(xml)
        self.assertFalse(response.succeeded)
        self.assertIn("Invalid Date", response.error_details)
        self.assertIn("Missing Ledger", response.error_details)

    def test_parse_ignored(self):
        xml = """
        <RESPONSE>
            <CREATED>0</CREATED>
            <ALTERED>0</ALTERED>
            <DELETED>0</DELETED>
            <STATUS>Ignored</STATUS>
        </RESPONSE>
        """
        response = parse_tally_response(xml)
        self.assertTrue(response.tally_response.get("is_ignored"))
        self.assertFalse(response.succeeded)

    def test_parse_invalid_xml(self):
        xml = "Not XML"
        response = parse_tally_response(xml)
        self.assertEqual(response.tally_status, "XML Error")
        self.assertEqual(response.raw_xml, "Not XML")

if __name__ == '__main__':
    unittest.main()
