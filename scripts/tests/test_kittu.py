import json
import logging
import sys
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.api import app

# ----------- CONFIGURATION -----------
client = TestClient(app)

ENDPOINTS = {
    "import_xml": "/import-tally/",
    "agent_query": "/ask-agent/",
    "modify_data": "/modify/",
    "get_customer_details": "/customer-details/",
    "list_ledgers": "/list-ledgers/"
}

SAMPLE_XML = "sample_tally.xml"
TEST_QUESTION = "Give me all overdue bills for company Acme Corp."
MODIFY_RECORD_ID = 123
DEFAULT_UPDATES = {"NAME": "Acme Corp Updated"}
CUSTOMER_NAME = "Acme Corp"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KittuTestScript")

# ----------- TEST FUNCTIONS -----------
def read_xml_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Could not read XML: {e}")
        sys.exit(1)

def get_index_by_id(record_id):
    resp = client.get(ENDPOINTS["list_ledgers"])
    if not resp or resp.status_code != 200:
        return None
    payload = resp.json()
    rows = payload.get("rows") or []
    # Try matching on common ID keys
    for idx, row in enumerate(rows):
        if ("ID" in row and str(row["ID"]) == str(record_id)) or ("id" in row and str(row["id"]) == str(record_id)):
            return idx
    return None

def test_import_tally_xml():
    xml_data = read_xml_file(SAMPLE_XML)
    resp = client.post(ENDPOINTS["import_xml"], json={"xml_input": xml_data})
    print("\n[Import XML] Response:")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200, f"API did not return OK for import: {resp.text}"
    rows = resp.json().get("rows", [])
    assert isinstance(rows, list)

def test_agent_query():
    question = TEST_QUESTION
    resp = client.post(ENDPOINTS["agent_query"], json={"query": question})
    print("\n[Agent Q&A] Response:")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200, f"API did not return OK for agent query: {resp.text}"
    assert "result" in resp.json()

def test_data_modification():
    record_id = MODIFY_RECORD_ID
    updates = DEFAULT_UPDATES
    idx = get_index_by_id(record_id)
    if idx is None:
        print(f"\n[Modify Data] Could not find idx for record_id={record_id}")
        idx = 0
    modify_payload = {
        "action": "update",
        "data": updates,
        "idx": idx
    }
    resp = client.post(ENDPOINTS["modify_data"], json=modify_payload)
    print("\n[Modify Data] Payload:")
    print(json.dumps(modify_payload, indent=2))
    print("[Modify Data] Response:")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200, f"API did not return OK for modification: {resp.text}"
    assert resp.json().get("status") == "success"

def test_data_deletion():
    record_id = MODIFY_RECORD_ID
    idx = get_index_by_id(record_id)
    if idx is None:
        print(f"\n[Delete Data] Could not find idx for record_id={record_id}")
        idx = 0
    delete_payload = {
        "action": "delete",
        "data": {},
        "idx": idx
    }
    resp = client.post(ENDPOINTS["modify_data"], json=delete_payload)
    print("\n[Delete Data] Payload:")
    print(json.dumps(delete_payload, indent=2))
    print("[Delete Data] Response:")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200, f"API did not return OK for deletion: {resp.text}"

def test_customer_details():
    customer_name = CUSTOMER_NAME
    resp = client.post(ENDPOINTS["get_customer_details"], json={"name": customer_name})
    print("\n[Customer Details] Response:")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200, f"API did not return OK for customer details: {resp.text}"
    assert resp.json().get("details") is not None

def test_customer_edge_cases():
    test_names = [" acme corp ", "ACME CORP", "acme corp", "Nonexistent Co"]
    for name in test_names:
        resp = client.post(ENDPOINTS["get_customer_details"], json={"name": name})
        print(f"\n[Customer Lookup: '{name}'] Response:")
        print(json.dumps(resp.json(), indent=2))
        assert resp.status_code == 200, f"API did not return OK for customer lookup: {resp.text}"

def test_modify_nonexistent():
    modify_payload = {
        "action": "update",
        "data": {"status": "paid"},
        "idx": 999999
    }
    resp = client.post(ENDPOINTS["modify_data"], json=modify_payload)
    print("\n[Modify Non-existent Record] Payload:")
    print(json.dumps(modify_payload, indent=2))
    print("[Modify Non-existent Record] Response:")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 400
    assert "Index 999999 is out of bounds" in resp.json().get("detail", "")

def test_broken_xml():
    bad_xml = "<root><data></root"
    resp = client.post(ENDPOINTS["import_xml"], json={"xml_input": bad_xml})
    print("\n[Broken XML Import] Response (should error gracefully):")
    print(json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200, "API did not return OK on broken XML (should provide error feedback)"
    assert resp.json().get("status") == "ok"

def test_list_data():
    resp = client.get(ENDPOINTS["list_ledgers"])
    print("\n[List Ledgers] Status Code:", resp.status_code)
    if resp.status_code != 200:
        print("[List Ledgers] Error Response Text:", resp.text)
    try:
        data = resp.json()
        print("[List Ledgers] Response:")
        print(json.dumps(data, indent=2))
        assert resp.status_code == 200, "API did not return OK for listing"
        assert isinstance(data.get("rows"), list)
    except json.JSONDecodeError as e:
        print(f"[List Ledgers] JSON Decode Error: {e}")
        print("[List Ledgers] Raw Response Text:", resp.text[:500])
        assert False, "Response was not valid JSON"

def test_full_agent_pipeline():
    xml_data = read_xml_file(SAMPLE_XML)
    import_resp = client.post(ENDPOINTS["import_xml"], json={"xml_input": xml_data}).json()
    # Try to extract first record's id
    rows = None
    if import_resp.get('rows') and isinstance(import_resp['rows'], list) and import_resp['rows']:
        rows = import_resp['rows']
    first_record_id = rows[0].get('ID') if rows and rows[0] else None
    if first_record_id:
        q_resp = client.post(ENDPOINTS["agent_query"], json={"query": TEST_QUESTION}).json()
        print("\n[Agent Q&A - Pre Modification] Response:", json.dumps(q_resp, indent=2))
        idx = get_index_by_id(first_record_id)
        if idx is None:
            idx = 0
        # Fetch the full row from the API for this idx
        resp_ledgers = client.get(ENDPOINTS["list_ledgers"])
        rows_ = resp_ledgers.json().get("rows", [])
        current_row = rows_[idx] if idx < len(rows_) else {}
        # Copy all fields, change NAME
        update_payload = dict(current_row)
        # Filter payload to only include allowed fields for update
        allowed_fields = {
            "NAME", "PARENT", "GSTIN", "PAN", "GSTREGISTRATIONTYPE", 
            "COUNTRYNAME", "STATENAME", "PINCODE", "EMAIL", "MOBILENUMBER", 
            "PHONENUMBER", "LEDSTATENAME", "INCOMETAXNUMBER", "MAILNAMES", 
            "ADDRESS", "ISBILLWISEON", "OPENINGBALANCE", "CREDITLIMIT"
        }
        # Ensure we are updating the name as intended
        update_payload["NAME"] = "Acme Corp Final"
        
        filtered_payload = {k: v for k, v in update_payload.items() if k in allowed_fields}
        
        modify_payload = {"action": "update", "data": filtered_payload, "idx": idx}
        
        # Patch TALLY_LIVE_UPDATE_ENABLED to False to avoid live sync error
        with patch("backend.api.TALLY_LIVE_UPDATE_ENABLED", False):
            resp = client.post(ENDPOINTS["modify_data"], json=modify_payload)
        
        assert resp.status_code == 200, f"API did not return OK for modification: {resp.text}"
        verify_resp = client.post(ENDPOINTS["agent_query"], json={"query": TEST_QUESTION}).json()
        print("\n[Agent Q&A - Post Modification] Response:", json.dumps(verify_resp, indent=2))
    else:
        print("No records available to chain-test.")
        assert False, "No records in sample XML for full agent pipeline test"

def test_api_robustness():
    bad_json = '{"xml_input": "<root></root>'
    resp = client.post(ENDPOINTS["import_xml"], content=bad_json, headers={"Content-Type": "application/json"})
    print("\n[Malformed JSON] Response:", resp.text)
    assert resp.status_code in (400, 422)
    resp = client.post(ENDPOINTS["import_xml"], content="<root></root>", headers={"Content-Type": "text/plain"})
    print("\n[Wrong Content-Type] Response:", resp.text)
    assert resp.status_code in (400, 415, 422)
    resp = client.post(ENDPOINTS["import_xml"], json={})
    print("\n[Missing Field] Response:", resp.text)
    assert resp.status_code == 422

# ----------- RUN TEST SUITE -----------
@pytest.fixture(scope="session", autouse=True)
def ensure_ledger_loaded():
    """Automatically POSTs sample XML to /import-tally/ before any tests."""
    xml_data = read_xml_file(SAMPLE_XML)
    resp = client.post(ENDPOINTS["import_xml"], json={"xml_input": xml_data})
    assert resp.status_code == 200, f"Could not load sample XML: {resp.text}"

if __name__ == "__main__":
    print("\n======= Kittu System End-to-End Test =======")

    # 1. Test XML Import and Parsing
    test_import_tally_xml()

    # 2. Test Agent Q&A Endpoint
    test_agent_query()

    # 3. Test Data Modification Endpoint (using ID->idx mapping)
    test_data_modification()

    # 4. Test Data Deletion (using ID->idx mapping)
    test_data_deletion()

    # 5. Test Customer Detail Lookup
    test_customer_details()

    # 6. Test Customer Lookup Edge Cases
    test_customer_edge_cases()

    # 7. Test Modify Non-existent Record
    test_modify_nonexistent()

    # 8. Test List Ledgers Endpoint
    test_list_data()

    # 9. Robustness: Test Invalid/Broken XML
    test_broken_xml()

    # 10. Test Full Agent Pipeline (import, agent Q, modify, agent Q)
    test_full_agent_pipeline()

    # 11. API Robustness error scenarios
    test_api_robustness()

    print("\n======= All tests completed! Manual inspection of output is recommended for best coverage. =======")
