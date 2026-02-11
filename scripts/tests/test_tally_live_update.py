from unittest.mock import MagicMock, patch

import pytest

from backend.tally_live_update import (
    TallyAPIError,
    TallyIgnoredError,
    create_voucher_in_tally,
    dispatch_tally_update,
    update_ledger_in_tally,
)
from backend.tally_xml_builder import (
    TallyXMLValidationError,
    build_ledger_update_xml,
    build_voucher_create_xml,
)


SUCCESS_LEDGER_RESPONSE = """
<ENVELOPE>
  <STATUS>1</STATUS>
  <ALTERED>1</ALTERED>
</ENVELOPE>
""".strip()


SUCCESS_VOUCHER_RESPONSE = """
<ENVELOPE>
  <STATUS>1</STATUS>
  <CREATED>1</CREATED>
</ENVELOPE>
""".strip()


ERROR_RESPONSE = """
<ENVELOPE>
  <LINEERROR>Invalid ledger</LINEERROR>
</ENVELOPE>
""".strip()


IGNORED_RESPONSE = """
<ENVELOPE>
  <STATUS>Ignored</STATUS>
</ENVELOPE>
""".strip()


def _mock_post(return_text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    mock_response.text = return_text
    return mock_response


def test_build_ledger_update_xml_has_action_alter():
    xml_payload = build_ledger_update_xml(
        company_name="Acme Ltd",
        ledger_name="GST Customers",
        updates={
            "GSTIN": "32ABCDE1234F2Z5",
            "PAN": "ABCDE1234F",
            "Address": ["Line 1", "Line 2"],
        },
    )
    assert 'LEDGER NAME="GST Customers" ACTION="Alter"' in xml_payload
    assert "<ADDRESS.LIST" in xml_payload
    assert "<GSTIN>32ABCDE1234F2Z5</GSTIN>" in xml_payload


def test_build_voucher_create_xml_contains_line_items():
    xml_payload = build_voucher_create_xml(
        company_name="Acme Ltd",
        voucher_fields={
            "DATE": "20250101",
            "VOUCHERTYPENAME": "Receipt",
            "PARTYLEDGERNAME": "Customer A",
            "NARRATION": "Payment received",
        },
        line_items=[
            {"ledger_name": "Customer A", "amount": -5000, "is_deemed_positive": True},
            {"ledger_name": "Cash", "amount": 5000, "is_deemed_positive": False},
        ],
    )
    assert "<VOUCHER VCHTYPE=\"Receipt\"" in xml_payload
    assert xml_payload.count("<ALLLEDGERENTRIES.LIST>") == 2
    assert "<LEDGERNAME>Cash</LEDGERNAME>" in xml_payload


@patch("backend.tally_live_update.requests.post")
def test_update_ledger_in_tally_success(mock_post):
    mock_post.return_value = _mock_post(SUCCESS_LEDGER_RESPONSE)
    response = update_ledger_in_tally(
        company_name="Acme Ltd",
        ledger_name="GST Customers",
        field_updates={
            "Address": ["Line 1", "Line 2"],
            "GSTIN": "32ABCDE1234F2Z5",
            "PAN": "ABCDE1234F",
        },
    )
    assert response.altered == 1
    payload_bytes = mock_post.call_args.kwargs["data"]
    assert b"ACTION=\"Alter\"" in payload_bytes


def test_update_ledger_in_tally_rejects_invalid_fields():
    with pytest.raises(TallyXMLValidationError):
        update_ledger_in_tally(
            company_name="Acme Ltd",
            ledger_name="GST Customers",
            field_updates={"status": "paid"},
        )


@patch("backend.tally_live_update.requests.post")
def test_update_ledger_in_tally_all_valid_fields_pass(mock_post):
    # All fields are whitelisted
    mock_post.return_value = _mock_post(SUCCESS_LEDGER_RESPONSE)
    try:
        update_ledger_in_tally(
            company_name="Test Co",
            ledger_name="MainLedger",
            field_updates={"NAME": "NewName"}
        )
    except TallyXMLValidationError as exc:
        assert False, f"No error expected, got {exc}"


def test_update_ledger_in_tally_all_invalid_fields_error():
    with pytest.raises(TallyXMLValidationError) as exc_info:
        update_ledger_in_tally(
            company_name="Test Co",
            ledger_name="WillFail",
            field_updates={"amount": 100, "status": "closed", "id": 99}
        )
    error = exc_info.value.args[0]
    assert isinstance(error, dict)
    assert error["status"] == "error"
    for field in ["amount", "status", "id"]:
        assert field in error["invalid_fields"]
    assert "NAME" in error["allowed_fields"]


def test_update_ledger_in_tally_mixed_fields_error():
    with pytest.raises(TallyXMLValidationError) as exc_info:
        update_ledger_in_tally(
            company_name="Test Co",
            ledger_name="WillFail",
            field_updates={"NAME": "X", "status": "closed", "GSTIN": "Y"}
        )
    error = exc_info.value.args[0]
    assert isinstance(error, dict)
    assert error["status"] == "error"
    assert "status" in error["invalid_fields"]
    assert "GSTIN" in error["allowed_fields"]


@patch("backend.tally_live_update.requests.post")
def test_create_voucher_in_tally_success(mock_post):
    mock_post.return_value = _mock_post(SUCCESS_VOUCHER_RESPONSE)
    response = create_voucher_in_tally(
        company_name="Acme Ltd",
        voucher_fields={
            "DATE": "20250101",
            "VOUCHERTYPENAME": "Receipt",
            "PARTYLEDGERNAME": "Customer A",
            "VOUCHERNUMBER": "RV-001",
            "NARRATION": "Payment received",
        },
        line_items=[
            {"ledger_name": "Customer A", "amount": -5000, "is_deemed_positive": True},
            {"ledger_name": "Cash", "amount": 5000, "is_deemed_positive": False},
        ],
    )
    assert response.created == 1
    payload_bytes = mock_post.call_args.kwargs["data"]
    assert b"<VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>" in payload_bytes


@patch("backend.tally_live_update.requests.post")
def test_dispatch_voucher_route(mock_post):
    mock_post.return_value = _mock_post(SUCCESS_VOUCHER_RESPONSE)
    response = dispatch_tally_update(
        entity_type="voucher",
        company_name="Acme Ltd",
        payload={
            "action": "create",
            "voucher": {
                "DATE": "20250101",
                "VOUCHERTYPENAME": "Payment",
                "PARTYLEDGERNAME": "Supplier A",
                "NARRATION": "Payment",
            },
            "line_items": [
                {"ledger_name": "Supplier A", "amount": 7500, "is_deemed_positive": False},
                {"ledger_name": "Bank", "amount": -7500, "is_deemed_positive": True},
            ],
        },
    )
    assert response.created == 1


def test_dispatch_rejects_unknown_ledger_fields():
    with pytest.raises(TallyXMLValidationError):
        dispatch_tally_update(
            entity_type="ledger",
            company_name="Acme Ltd",
            payload={"ledger_name": "GST Customers", "fields": {"status": "paid"}},
        )


@patch("backend.tally_live_update.requests.post")
def test_tally_api_error_surface(mock_post):
    mock_post.return_value = _mock_post(ERROR_RESPONSE)
    with pytest.raises(TallyAPIError) as exc_info:
        update_ledger_in_tally(
            company_name="Acme Ltd",
            ledger_name="GST Customers",
            field_updates={"GSTIN": "32ABCDE1234F2Z5"},
        )
    assert "Invalid ledger" in str(exc_info.value)
    assert exc_info.value.response


@patch("backend.tally_live_update.requests.post")
def test_tally_ignored_error_surface(mock_post):
    mock_post.return_value = _mock_post(IGNORED_RESPONSE)
    with pytest.raises(TallyIgnoredError) as exc_info:
        update_ledger_in_tally(
            company_name="Acme Ltd",
            ledger_name="GST Customers",
            field_updates={"GSTIN": "32ABCDE1234F2Z5"},
        )
    assert exc_info.value.response is not None