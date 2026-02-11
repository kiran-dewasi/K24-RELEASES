import unittest
from unittest.mock import MagicMock, patch
from backend.tally_connector import TallyConnector
from backend.tally_response_parser import parse_tally_response
from requests.exceptions import RequestException

class TestTallyRobustness(unittest.TestCase):
    def setUp(self):
        self.connector = TallyConnector()

    def test_parser_success_created(self):
        xml = """<ENVELOPE>
        <BODY><IMPORTDATA><RESPONSES>
        <CREATED>1</CREATED><ALTERED>0</ALTERED><DELETED>0</DELETED>
        <ERRORS>0</ERRORS>
        </RESPONSES></IMPORTDATA></BODY>
        </ENVELOPE>"""
        result = parse_tally_response(xml)
        self.assertTrue(result["success"])
        self.assertEqual(result["created"], 1)

    def test_parser_failure_lineerror(self):
        xml = """<ENVELOPE>
        <BODY><IMPORTDATA><REQUESTDESC><REQUESTDATA>
        <TALLYMESSAGE><LINEERROR>Field GSTIN is invalid</LINEERROR></TALLYMESSAGE>
        </REQUESTDATA></REQUESTDESC></IMPORTDATA></BODY>
        </ENVELOPE>"""
        result = parse_tally_response(xml)
        self.assertFalse(result["success"])
        self.assertIn("Field GSTIN is invalid", result["errors"])

    def test_parser_failure_error_count(self):
        xml = """<ENVELOPE>
        <BODY><IMPORTDATA><RESPONSES>
        <CREATED>0</CREATED><ALTERED>0</ALTERED><ERRORS>1</ERRORS>
        </RESPONSES></IMPORTDATA></BODY>
        </ENVELOPE>"""
        result = parse_tally_response(xml)
        self.assertFalse(result["success"])
        self.assertIn("Tally reported 1 errors", result["errors"][0])

    @patch('backend.tally_connector.requests.post')
    def test_connector_push_xml_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.text = """<ENVELOPE><BODY><IMPORTDATA><RESPONSES>
        <CREATED>1</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS>
        </RESPONSES></IMPORTDATA></BODY></ENVELOPE>"""
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.connector.push_xml("<test></test>")
        self.assertTrue(result["success"])
        self.assertEqual(result["created"], 1)

    @patch('backend.tally_connector.requests.post')
    def test_connector_push_xml_connection_error(self, mock_post):
        mock_post.side_effect = RequestException("Connection refused")

        result = self.connector.push_xml("<test></test>")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "Connection Error")

if __name__ == '__main__':
    unittest.main()
