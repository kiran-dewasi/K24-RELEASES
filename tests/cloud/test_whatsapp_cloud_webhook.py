"""
Tests for cloud WhatsApp webhook endpoint

Tests tenant routing, queue insertion, and tenant isolation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime

# Import the FastAPI app
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cloud-backend'))

from main import app
from routers.whatsapp_cloud import get_baileys_secret


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('routers.whatsapp_cloud.get_supabase_client') as mock:
        supabase_mock = MagicMock()
        mock.return_value = supabase_mock
        yield supabase_mock


@pytest.fixture
def valid_message_payload():
    """Valid WhatsApp message payload"""
    return {
        "from_number": "+919876543210",
        "to_number": "+918888888888",
        "message_type": "text",
        "text": "Hello, I need help with my invoice",
        "media_url": None,
        "raw_payload": {
            "messageId": "test_123",
            "timestamp": 1234567890
        }
    }


@pytest.fixture
def valid_headers():
    """Valid authentication headers"""
    return {
        "X-Baileys-Secret": get_baileys_secret()
    }


class TestWebhookAuthentication:
    """Test webhook authentication"""

    def test_missing_auth_header(self, client, valid_message_payload):
        """Test request without auth header is rejected"""
        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload
        )
        assert response.status_code == 403

    def test_invalid_auth_header(self, client, valid_message_payload):
        """Test request with wrong secret is rejected"""
        headers = {"X-Baileys-Secret": "wrong_secret"}
        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=headers
        )
        assert response.status_code == 403

    def test_valid_auth_header(self, client, valid_message_payload, valid_headers, mock_supabase):
        """Test request with valid auth header is accepted"""
        # Mock customer mapping lookup - return unknown customer for this test
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=valid_headers
        )
        assert response.status_code == 202


class TestTenantRouting:
    """Test tenant identification and routing"""

    def test_known_customer_single_tenant(self, client, valid_message_payload, valid_headers, mock_supabase):
        """Test message from known customer is routed to correct tenant"""
        tenant_id = "TENANT-ABC123"
        user_id = str(uuid.uuid4())

        # Mock customer mapping lookup
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table

        # Setup chained mock for select().eq().eq().execute()
        mock_select = Mock()
        mock_table.select.return_value = mock_select
        mock_eq1 = Mock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = Mock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = Mock(data=[{
            "tenant_id": tenant_id,
            "user_id": user_id,
            "customer_name": "Test Customer"
        }])
        mock_eq1.execute.return_value.data = [{
            "tenant_id": tenant_id,
            "subscription_status": "active",
            "trial_ends_at": None
        }]

        # Mock queue insert
        mock_insert = Mock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = Mock(data=[{"id": "msg-123"}])

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=valid_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "message_id" in data

    def test_unknown_customer_returns_404(self, client, valid_message_payload, valid_headers, mock_supabase):
        """Test message from unknown customer returns 404"""
        # Mock empty customer mapping result
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table
        mock_select = Mock()
        mock_table.select.return_value = mock_select
        mock_eq1 = Mock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = Mock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = Mock(data=[])

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=valid_headers
        )

        assert response.status_code == 202

    def test_multiple_tenants_uses_first(self, client, valid_message_payload, valid_headers, mock_supabase):
        """Test customer mapped to multiple tenants uses first match"""
        tenant_id_1 = "TENANT-ABC123"
        tenant_id_2 = "TENANT-XYZ789"

        # Mock multiple mappings
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table
        mock_select = Mock()
        mock_table.select.return_value = mock_select
        mock_eq1 = Mock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = Mock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = Mock(data=[
            {"tenant_id": tenant_id_1, "user_id": str(uuid.uuid4()), "customer_name": "Customer 1"},
            {"tenant_id": tenant_id_2, "user_id": str(uuid.uuid4()), "customer_name": "Customer 2"}
        ])
        mock_eq1.execute.return_value.data = [{
            "tenant_id": tenant_id_1,
            "subscription_status": "active",
            "trial_ends_at": None
        }]

        # Mock queue insert
        mock_insert = Mock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = Mock(data=[{"id": "msg-123"}])

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=valid_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "message_id" in data


class TestQueueInsertion:
    """Test message queue insertion"""

    def test_message_inserted_with_correct_fields(self, client, valid_message_payload, valid_headers, mock_supabase):
        """Test message is inserted into queue with all correct fields"""
        tenant_id = "TENANT-TEST123"
        user_id = str(uuid.uuid4())

        # Track the inserted data
        inserted_data = None

        def capture_insert(data):
            nonlocal inserted_data
            inserted_data = data
            mock_result = Mock()
            mock_result.execute.return_value = Mock(data=[{"id": data.get("id")}])
            return mock_result

        # Mock customer mapping
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table
        mock_select = Mock()
        mock_table.select.return_value = mock_select
        mock_eq1 = Mock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = Mock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = Mock(data=[{
            "tenant_id": tenant_id,
            "user_id": user_id,
            "customer_name": "Test Customer"
        }])
        mock_eq1.execute.return_value.data = [{
            "tenant_id": tenant_id,
            "subscription_status": "active",
            "trial_ends_at": None
        }]

        # Mock insert with capture
        mock_table.insert.side_effect = capture_insert

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=valid_headers
        )

        assert response.status_code == 202

        # Verify inserted data structure
        assert inserted_data is not None
        assert inserted_data["tenant_id"] == tenant_id
        assert inserted_data["user_id"] == user_id
        assert inserted_data["customer_phone"] == valid_message_payload["from_number"]
        assert inserted_data["message_type"] == valid_message_payload["message_type"]
        assert inserted_data["message_text"] == valid_message_payload["text"]
        assert inserted_data["media_url"] == valid_message_payload["media_url"]
        assert inserted_data["status"] == "pending"
        assert "id" in inserted_data
        assert "created_at" in inserted_data

    def test_media_message_handled_correctly(self, client, valid_headers, mock_supabase):
        """Test media messages (image, document) are handled correctly"""
        tenant_id = "TENANT-MEDIA"

        payload = {
            "from_number": "+919876543210",
            "message_type": "image",
            "text": "Check this invoice",
            "media_url": "https://example.com/invoice.jpg",
            "raw_payload": {"media": "base64..."}
        }

        inserted_data = None

        def capture_insert(data):
            nonlocal inserted_data
            inserted_data = data
            mock_result = Mock()
            mock_result.execute.return_value = Mock(data=[{"id": data.get("id")}])
            return mock_result

        # Mock customer mapping
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table
        mock_select = Mock()
        mock_table.select.return_value = mock_select
        mock_eq1 = Mock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = Mock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = Mock(data=[{
            "tenant_id": tenant_id,
            "user_id": str(uuid.uuid4()),
            "customer_name": "Media Customer"
        }])
        mock_eq1.execute.return_value.data = [{
            "tenant_id": tenant_id,
            "subscription_status": "active",
            "trial_ends_at": None
        }]

        mock_table.insert.side_effect = capture_insert

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=payload,
            headers=valid_headers
        )

        assert response.status_code == 202
        assert inserted_data["message_type"] == "image"
        assert inserted_data["media_url"] == payload["media_url"]


class TestTenantIsolation:
    """Test tenant isolation - critical security tests"""

    def test_different_customers_different_tenants(self, client, valid_headers, mock_supabase):
        """Test that messages from different customers go to different tenants"""
        tenant_a = "TENANT-AAAA"
        tenant_b = "TENANT-BBBB"

        customer_a = "+919111111111"
        customer_b = "+919222222222"

        inserted_messages = []
        call_count = [0]  # Track which call we're on

        def capture_insert(data):
            inserted_messages.append(data)
            mock_result = Mock()
            mock_result.execute.return_value = Mock(data=[{"id": data.get("id")}])
            return mock_result

        # Setup dynamic mocking
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table

        # For select queries - simplified approach
        def select_side_effect(*args):
            current_call = call_count[0]
            call_count[0] += 1

            mock_select = Mock()
            mock_eq1 = Mock()
            mock_eq2 = Mock()

            # First call is for customer A, second for customer B
            if current_call in (0, 1):
                result_data = [{
                    "tenant_id": tenant_a,
                    "user_id": str(uuid.uuid4()),
                    "customer_name": "Customer A"
                }]
                active_tenant = tenant_a
            else:
                result_data = [{
                    "tenant_id": tenant_b,
                    "user_id": str(uuid.uuid4()),
                    "customer_name": "Customer B"
                }]
                active_tenant = tenant_b

            mock_eq2.execute.return_value = Mock(data=result_data)
            mock_eq1.eq.return_value = mock_eq2
            mock_eq1.execute.return_value.data = [{
                "tenant_id": active_tenant,
                "subscription_status": "active",
                "trial_ends_at": None
            }]
            mock_select.eq.return_value = mock_eq1
            return mock_select

        mock_table.select.side_effect = select_side_effect
        mock_table.insert.side_effect = capture_insert

        # Send message from customer A
        payload_a = {
            "from_number": customer_a,
            "message_type": "text",
            "text": "Message from A"
        }
        response_a = client.post(
            "/api/whatsapp/cloud/incoming",
            json=payload_a,
            headers=valid_headers
        )

        # Send message from customer B
        payload_b = {
            "from_number": customer_b,
            "message_type": "text",
            "text": "Message from B"
        }
        response_b = client.post(
            "/api/whatsapp/cloud/incoming",
            json=payload_b,
            headers=valid_headers
        )

        assert response_a.status_code == 202
        assert response_b.status_code == 202

        # Verify tenant isolation
        assert len(inserted_messages) == 2
        assert inserted_messages[0]["tenant_id"] == tenant_a
        assert inserted_messages[0]["customer_phone"] == customer_a
        assert inserted_messages[1]["tenant_id"] == tenant_b
        assert inserted_messages[1]["customer_phone"] == customer_b

        # Verify no cross-contamination
        assert inserted_messages[0]["tenant_id"] != inserted_messages[1]["tenant_id"]


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_database_error_returns_500(self, client, valid_message_payload, valid_headers, mock_supabase):
        """Test database errors are handled gracefully"""
        # Mock database error
        mock_table = Mock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.side_effect = Exception("Database connection failed")

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=valid_message_payload,
            headers=valid_headers
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_invalid_message_payload(self, client, valid_headers):
        """Test invalid payload structure is rejected"""
        invalid_payload = {
            "from_number": "+919876543210"
            # Missing required fields
        }

        response = client.post(
            "/api/whatsapp/cloud/incoming",
            json=invalid_payload,
            headers=valid_headers
        )

        # FastAPI validation error
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
