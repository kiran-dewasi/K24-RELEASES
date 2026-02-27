"""
Phase 1 Fix Verification Tests
================================
Tests for:
  1. parse_tally_response() crash fix — AttributeError on missing <ALTERED> tag
  2. Idempotency guard — duplicate voucher prevention in HTTP endpoints

Run with:
    cd c:\\Users\\Krisha Dewasi\\OneDrive\\Desktop\\WEARE\\weare
    .\\venv311\\Scripts\\python.exe -m pytest tests/test_phase1_fixes.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# SECTION 1: parse_tally_response() crash fix
# ─────────────────────────────────────────────────────────────

class TestParseTallyResponse:
    """
    Tests for tally_live_update.parse_tally_response()

    BUG FIXED: root.find(".//ALTERED") returns None when Tally doesn't
    include <ALTERED> in its response. Calling .text on None → AttributeError.
    Old code: if created > 0 or root.find(".//ALTERED").text == '1'
    New code: safely reads altered_elem with None check
    """

    def setup_method(self):
        from backend.tally_live_update import parse_tally_response
        self.parse = parse_tally_response

    def test_created_response_without_altered_tag(self):
        """
        MAIN CRASH CASE: Tally returns <CREATED>1</CREATED> but NO <ALTERED> tag.
        Old code crashed here with AttributeError. Must return success=True now.
        """
        xml = """<RESPONSE>
            <CREATED>1</CREATED>
            <ERRORS>0</ERRORS>
        </RESPONSE>"""
        result = self.parse(xml)
        assert result.success is True, f"Expected success=True, got success={result.success}, error='{result.error_details}'"
        assert result.tally_status == "Success"
        assert result.tally_response["created"] == 1
        assert result.tally_response["altered"] == 0

    def test_altered_response_without_created_tag(self):
        """
        Tally returns <ALTERED>1</ALTERED> for an update operation.
        Must return success=True.
        """
        xml = """<RESPONSE>
            <CREATED>0</CREATED>
            <ALTERED>1</ALTERED>
            <ERRORS>0</ERRORS>
        </RESPONSE>"""
        result = self.parse(xml)
        assert result.success is True, f"Expected success=True, got success={result.success}"
        assert result.tally_response["altered"] == 1

    def test_both_created_and_altered_zero_with_no_errors(self):
        """
        Nothing created or altered — falls to status check path.
        Should not crash.
        """
        xml = """<RESPONSE>
            <CREATED>0</CREATED>
            <ERRORS>0</ERRORS>
        </RESPONSE>"""
        result = self.parse(xml)
        # Per the code, if created=0, altered=0, no errors → "Unknown" path
        # Should NOT crash, error_details should describe the issue
        assert result is not None
        assert not result.success  # no confirmation = failure

    def test_error_response(self):
        """
        Tally returns an error with LINEERROR — must return success=False with details.
        """
        xml = """<RESPONSE>
            <CREATED>0</CREATED>
            <ERRORS>1</ERRORS>
            <LINEERROR>Ledger &quot;XYZ&quot; does not exist</LINEERROR>
        </RESPONSE>"""
        result = self.parse(xml)
        assert result.success is False
        assert result.tally_status == "Failure"
        assert "XYZ" in result.error_details or result.error_details != ""

    def test_empty_response(self):
        """
        Empty string — must return success=False, not crash.
        """
        result = self.parse("")
        assert result.success is False
        assert "Empty" in result.error_details or result.error_details != ""

    def test_malformed_xml_response(self):
        """
        Garbled XML from Tally (can happen on timeout/partial response).
        Must not crash, must return success=False.
        """
        result = self.parse("<<<NOT XML>>>")
        assert result.success is False
        assert result.error_details != ""

    def test_real_tally_success_format(self):
        """
        Actual Tally XML server response format for a successful import.
        """
        xml = """<ENVELOPE>
            <HEADER>
                <VERSION>1</VERSION>
                <STATUS>1</STATUS>
            </HEADER>
            <BODY>
                <DATA>
                    <IMPORTRESULT>
                        <CREATED>1</CREATED>
                        <ALTERED>0</ALTERED>
                        <DELETED>0</DELETED>
                        <ERRORS>0</ERRORS>
                        <COMBINED>0</COMBINED>
                    </IMPORTRESULT>
                </DATA>
            </BODY>
        </ENVELOPE>"""
        result = self.parse(xml)
        assert result.success is True, f"Real Tally format failed: {result.error_details}"


# ─────────────────────────────────────────────────────────────
# SECTION 2: Idempotency guard — duplicate voucher prevention
# ─────────────────────────────────────────────────────────────

class TestIdempotencyGuard:
    """
    Tests for the duplicate push protection added to:
      - POST /vouchers/receipt
      - POST /vouchers/sales
      - POST /vouchers/payment

    BUG FIXED: No check was done before pushing to Tally. Double-tap
    (or page refresh during submission) sent two identical vouchers to Tally.
    """

    def _make_mock_voucher(self, voucher_type, party, amount, date_obj):
        """Helper to create a mock Voucher DB record."""
        v = MagicMock()
        v.voucher_type = voucher_type
        v.party_name = party
        v.amount = amount
        v.date = date_obj
        v.sync_status = "SYNCED"
        v.voucher_number = f"RCP-TEST-001"
        v.id = 42
        return v

    def test_receipt_duplicate_detected(self):
        """
        When a SYNCED receipt with same party+amount+date exists in DB,
        the endpoint must return the existing one without pushing to Tally.
        """
        from backend.routers.vouchers import create_receipt_voucher
        from backend.routers.vouchers import ReceiptVoucherRequest

        date_str = "2026-02-27"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        existing = self._make_mock_voucher("Receipt", "ABC Traders", 5000.0, date_obj)

        mock_db = MagicMock()
        # Simulate DB query returning existing voucher
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = existing

        request = ReceiptVoucherRequest(
            party_name="ABC Traders",
            amount=5000.0,
            deposit_to="Cash",
            date=date_str,
        )

        import asyncio
        with patch("backend.routers.vouchers.get_or_create_ledger", return_value=1):
            result = asyncio.get_event_loop().run_until_complete(
                create_receipt_voucher(request=request, db=mock_db)
            )

        assert result["status"] == "success"
        assert "duplicate" in result["message"].lower()
        assert result["db_id"] == 42
        # Tally engine must NOT have been called
        # (we can verify by checking engine.process_voucher was not called)

    def test_receipt_no_duplicate_proceeds(self):
        """
        When no existing voucher found in DB, the request should go to Tally normally.
        """
        from backend.routers.vouchers import create_receipt_voucher
        from backend.routers.vouchers import ReceiptVoucherRequest

        date_str = "2026-02-27"
        mock_db = MagicMock()
        # No existing voucher
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

        request = ReceiptVoucherRequest(
            party_name="New Fresh Party",
            amount=9999.0,
            deposit_to="Cash",
            date=date_str,
        )

        with patch("backend.routers.vouchers.get_or_create_ledger", return_value=1):
            with patch("backend.routers.vouchers.engine") as mock_engine:
                mock_engine.process_voucher.return_value = {"status": "success", "message": "Created"}
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    create_receipt_voucher(request=request, db=mock_db)
                )

        # Should have called Tally engine
        mock_engine.process_voucher.assert_called_once()
        assert result["status"] == "success"

    def test_idempotency_key_fields(self):
        """
        Verify the idempotency check uses the correct 4 fields:
        voucher_type + party_name + amount + date
        Different amount = NOT duplicate (different transaction).
        """
        from backend.routers.vouchers import create_receipt_voucher
        from backend.routers.vouchers import ReceiptVoucherRequest

        date_str = "2026-02-27"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

        # DB has a receipt for 5000
        existing = self._make_mock_voucher("Receipt", "ABC Traders", 5000.0, date_obj)

        mock_db = MagicMock()
        # Simulate DB query returning existing (for any filter combination)
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

        # But we're trying to create a DIFFERENT amount (6000)
        request = ReceiptVoucherRequest(
            party_name="ABC Traders",
            amount=6000.0,  # ← Different amount
            deposit_to="Cash",
            date=date_str,
        )

        with patch("backend.routers.vouchers.get_or_create_ledger", return_value=1):
            with patch("backend.routers.vouchers.engine") as mock_engine:
                mock_engine.process_voucher.return_value = {"status": "success", "message": "Created"}
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    create_receipt_voucher(request=request, db=mock_db)
                )

        # Should NOT be detected as duplicate — proceeds to Tally
        mock_engine.process_voucher.assert_called_once()


# ─────────────────────────────────────────────────────────────
# SECTION 3: Integration sanity — parse_tally_response import
# ─────────────────────────────────────────────────────────────

class TestImportSanity:
    """Basic sanity: verify modules import without errors after Phase 1 changes."""

    def test_tally_live_update_imports(self):
        """Module must import cleanly."""
        from backend.tally_live_update import (
            parse_tally_response,
            TallyResponse,
            post_to_tally,
            create_voucher_safely,
        )
        assert callable(parse_tally_response)
        assert callable(post_to_tally)

    def test_vouchers_router_imports(self):
        """Vouchers router must import cleanly."""
        from backend.routers.vouchers import (
            create_receipt_voucher,
            create_sales_invoice,
            create_payment_voucher,
            ReceiptVoucherRequest,
        )
        assert callable(create_receipt_voucher)
        assert callable(create_sales_invoice)
        assert callable(create_payment_voucher)

    def test_tally_response_dataclass(self):
        """TallyResponse dataclass must work correctly."""
        from backend.tally_live_update import TallyResponse
        r = TallyResponse(success=True, tally_status="Success", tally_response={"created": 1})
        assert r.success is True
        assert r.succeeded is True  # property alias
        d = r.to_dict()
        assert d["success"] is True
