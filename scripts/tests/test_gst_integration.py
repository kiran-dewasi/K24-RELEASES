import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.api import app
from backend.tally_live_update import update_ledger_in_tally, TallyXMLValidationError

client = TestClient(app)
HEADERS = {"x-api-key": "k24-secret-key-123"}

def test_validate_gstin_endpoint():
    # Valid GSTIN
    response = client.post("/reports/validate", json={"gstin": "27ABCDE1234F1Z5"}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["valid"] == True
    assert response.json()["state"] == "Maharashtra"

    # Invalid GSTIN (Length)
    response = client.post("/reports/validate", json={"gstin": "27ABCDE1234F1Z"}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["valid"] == False
    assert "length" in response.json()["error"].lower() or "15" in response.json()["error"]

    # Invalid GSTIN (State Code)
    response = client.post("/reports/validate", json={"gstin": "99ABCDE1234F1Z5"}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["valid"] == False
    assert "state code" in response.json()["error"].lower()

def test_calculate_tax_endpoint():
    # Intra-state (Same state)
    response = client.post("/reports/calculate", json={
        "amount": 1000,
        "party_gstin": "27ABCDE1234F1Z5",
        "company_gstin": "27XYZDE1234F1Z5",
        "tax_rate": 18.0
    }, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Intra-State"
    assert data["cgst"] == 90.0
    assert data["sgst"] == 90.0
    assert data["igst"] == 0.0
    assert data["total_tax"] == 180.0

    # Inter-state (Different state)
    response = client.post("/reports/calculate", json={
        "amount": 1000,
        "party_gstin": "29ABCDE1234F1Z5", # Karnataka
        "company_gstin": "27XYZDE1234F1Z5", # Maharashtra
        "tax_rate": 18.0
    }, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Inter-State"
    assert data["igst"] == 180.0
    assert data["cgst"] == 0.0
    assert data["sgst"] == 0.0

@patch("backend.tally_live_update.post_to_tally")
def test_ledger_update_gstin_validation(mock_post):
    # Mock successful response
    mock_post.return_value = MagicMock(succeeded=True)

    # Valid GSTIN
    update_ledger_in_tally(
        company_name="Test Company",
        ledger_name="Test Ledger",
        field_updates={"GSTIN": "27ABCDE1234F1Z5"}
    )
    mock_post.assert_called_once()

    # Invalid GSTIN
    with pytest.raises(TallyXMLValidationError) as excinfo:
        update_ledger_in_tally(
            company_name="Test Company",
            ledger_name="Test Ledger",
            field_updates={"GSTIN": "INVALID_GSTIN"}
        )
    assert "Invalid GSTIN" in str(excinfo.value)

if __name__ == "__main__":
    # Manually run tests if executed as script
    try:
        test_validate_gstin_endpoint()
        print("✅ test_validate_gstin_endpoint passed")
        test_calculate_tax_endpoint()
        print("✅ test_calculate_tax_endpoint passed")
        test_ledger_update_gstin_validation()
        print("✅ test_ledger_update_gstin_validation passed")
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
