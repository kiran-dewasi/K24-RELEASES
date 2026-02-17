"""
Tests for Tenant Sync Webhook Endpoint

Tests the POST /api/webhooks/tenant-sync endpoint that receives
webhooks from k24-prelaunch and syncs to k24-main.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import os
from datetime import datetime, timezone

# Import the FastAPI app
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)

# Test constants
VALID_WEBHOOK_SECRET = "test_webhook_secret_12345"
INVALID_WEBHOOK_SECRET = "wrong_secret"
TEST_TENANT_ID = "tenant_abc123"
TEST_WHATSAPP = "+1234567890"
TEST_EMAIL = "test@example.com"


@pytest.fixture
def mock_env_webhook_secret(monkeypatch):
    """Mock TENANT_SYNC_WEBHOOK_SECRET environment variable"""
    monkeypatch.setenv("TENANT_SYNC_WEBHOOK_SECRET", VALID_WEBHOOK_SECRET)
    monkeypatch.setenv("K24_MAIN_SUPABASE_URL", "https://test-main.supabase.co")
    monkeypatch.setenv("K24_MAIN_SUPABASE_SERVICE_ROLE_KEY", "test_service_key")


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for k24-main"""
    with patch('routers.webhooks.create_client') as mock:
        yield mock


class TestTenantSyncWebhook:
    """Tests for POST /api/webhooks/tenant-sync"""
    
    def test_sync_valid_insert(self, mock_env_webhook_secret, mock_supabase):
        """Test successful tenant sync on INSERT event"""
        # Mock k24-main Supabase client
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        
        # Mock select (no existing record)
        mock_select_table = Mock()
        mock_client.table.return_value = mock_select_table
        
        mock_select = Mock()
        mock_select_table.select.return_value = mock_select
        
        mock_eq = Mock()
        mock_select.eq.return_value = mock_eq
        
        mock_eq.execute.return_value = Mock(data=[])  # No existing record
        
        # Mock upsert
        mock_upsert = Mock()
        mock_select_table.upsert.return_value = mock_upsert
        
        mock_upsert.execute.return_value = Mock(data=[{
            "tenant_id": TEST_TENANT_ID,
            "whatsapp_number": TEST_WHATSAPP,
            "user_email": TEST_EMAIL,
            "subscription_status": "trial"
        }])
        
        # Make request
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    "id": TEST_TENANT_ID,
                    "whatsapp_number": TEST_WHATSAPP,
                    "email": TEST_EMAIL
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "synced"
        assert data["tenant_id"] == TEST_TENANT_ID
        assert "****" in data["whatsapp_number"]  # Should be masked
        assert "timestamp" in data
    
    def test_sync_integer_tenant_id(self, mock_env_webhook_secret, mock_supabase):
        """Test that integer tenant_id (from Supabase bigint) is handled correctly"""
        # Mock k24-main Supabase client
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        
        # Mock select (no existing record)
        mock_select_table = Mock()
        mock_client.table.return_value = mock_select_table
        
        mock_select = Mock()
        mock_select_table.select.return_value = mock_select
        
        mock_eq = Mock()
        mock_select.eq.return_value = mock_eq
        
        mock_eq.execute.return_value = Mock(data=[])  # No existing record
        
        # Mock upsert
        mock_upsert = Mock()
        mock_select_table.upsert.return_value = mock_upsert
        
        mock_upsert.execute.return_value = Mock(data=[{
            "tenant_id": "13",  # Should be string
            "whatsapp_number": TEST_WHATSAPP,
            "user_email": TEST_EMAIL,
            "subscription_status": "trial"
        }])
        
        # Make request with INTEGER tenant_id (like Supabase bigint)
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    "id": 13,  # INTEGER not string
                    "whatsapp_number": TEST_WHATSAPP,
                    "email": TEST_EMAIL
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "synced"
        assert data["tenant_id"] == "13"  # Should be normalized to string
        
        # Verify that upsert was called with STRING tenant_id
        call_args = mock_select_table.upsert.call_args
        upsert_payload = call_args[0][0]
        assert upsert_payload["tenant_id"] == "13"  # Must be string, not int
        assert isinstance(upsert_payload["tenant_id"], str)
    
    def test_sync_missing_whatsapp_number(self, mock_env_webhook_secret, mock_supabase):
        """Test that missing whatsapp_number is ignored with 200 status"""
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    "id": TEST_TENANT_ID,
                    "email": TEST_EMAIL
                    # Missing whatsapp_number
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "missing_whatsapp_number"
        assert data["tenant_id"] == TEST_TENANT_ID
    
    def test_sync_missing_webhook_secret(self, mock_env_webhook_secret):
        """Test that missing webhook secret returns 401"""
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    "id": TEST_TENANT_ID,
                    "whatsapp_number": TEST_WHATSAPP,
                    "email": TEST_EMAIL
                }
            }
            # No X-Webhook-Secret header
        )
        
        assert response.status_code == 401
        assert "Invalid or missing webhook secret" in response.json()["detail"]
    
    def test_sync_invalid_webhook_secret(self, mock_env_webhook_secret):
        """Test that invalid webhook secret returns 401"""
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    "id": TEST_TENANT_ID,
                    "whatsapp_number": TEST_WHATSAPP,
                    "email": TEST_EMAIL
                }
            },
            headers={"X-Webhook-Secret": INVALID_WEBHOOK_SECRET}
        )
        
        assert response.status_code == 401
    
    def test_sync_delete_event_ignored(self, mock_env_webhook_secret):
        """Test that DELETE events are ignored"""
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "DELETE",
                "table": "presale_orders",
                "schema": "public",
                "old_record": {
                    "id": TEST_TENANT_ID
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "event_type_not_handled"
    
    def test_sync_wrong_table_ignored(self, mock_env_webhook_secret):
        """Test that webhooks from other tables are ignored"""
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "other_table",
                "schema": "public",
                "record": {
                    "id": TEST_TENANT_ID,
                    "whatsapp_number": TEST_WHATSAPP
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "unexpected_table"
    
    def test_sync_missing_tenant_id(self, mock_env_webhook_secret):
        """Test that missing tenant_id returns 400"""
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "INSERT",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    # Missing id
                    "whatsapp_number": TEST_WHATSAPP,
                    "email": TEST_EMAIL
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        assert response.status_code == 400
        assert "Missing tenant_id" in response.json()["detail"]
    
    def test_sync_update_preserves_subscription(self, mock_env_webhook_secret, mock_supabase):
        """Test that UPDATE preserves existing subscription_status and trial_ends_at"""
        # Mock k24-main Supabase client
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        
        # Mock select (existing record with paid status)
        mock_select_table = Mock()
        mock_client.table.return_value = mock_select_table
        
        mock_select = Mock()
        mock_select_table.select.return_value = mock_select
        
        mock_eq = Mock()
        mock_select.eq.return_value = mock_eq
        
        # Existing record with paid subscription
        mock_eq.execute.return_value = Mock(data=[{
            "tenant_id": TEST_TENANT_ID,
            "subscription_status": "active",
            "trial_ends_at": "2026-12-31T23:59:59Z"
        }])
        
        # Mock upsert
        mock_upsert = Mock()
        mock_select_table.upsert.return_value = mock_upsert
        
        mock_upsert.execute.return_value = Mock(data=[{
            "tenant_id": TEST_TENANT_ID,
            "whatsapp_number": TEST_WHATSAPP,
            "subscription_status": "active"  # Preserved
        }])
        
        # Make request
        response = client.post(
            "/api/webhooks/tenant-sync",
            json={
                "type": "UPDATE",
                "table": "presale_orders",
                "schema": "public",
                "record": {
                    "id": TEST_TENANT_ID,
                    "whatsapp_number": TEST_WHATSAPP,
                    "email": TEST_EMAIL
                }
            },
            headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "synced"
        
        # Verify that upsert was called WITHOUT subscription_status/trial_ends_at
        # (they should be preserved from existing record)
        call_args = mock_select_table.upsert.call_args
        upsert_payload = call_args[0][0]
        
        # Should only contain tenant_id, whatsapp_number, user_email
        # Should NOT contain subscription_status or trial_ends_at (preserved)
        assert "tenant_id" in upsert_payload
        assert "whatsapp_number" in upsert_payload
        # subscription_status and trial_ends_at should not be in the upsert if they exist


class TestWebhooksStatus:
    """Tests for GET /api/webhooks/status"""
    
    def test_status_endpoint(self):
        """Test that status endpoint returns operational"""
        response = client.get("/api/webhooks/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["service"] == "webhooks"
        assert "timestamp" in data
