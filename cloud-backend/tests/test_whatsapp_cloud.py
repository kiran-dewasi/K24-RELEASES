import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import os
from datetime import datetime, timezone

# Import the FastAPI app
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from routers.whatsapp_cloud import JobCompletion

client = TestClient(app)

# Test constants
VALID_API_KEY = "test_desktop_api_key_12345"
INVALID_API_KEY = "wrong_key"
TEST_TENANT_ID = "test_tenant_123"
TEST_MESSAGE_ID = "msg_12345"


@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Mock DESKTOP_API_KEY environment variable"""
    monkeypatch.setenv("DESKTOP_API_KEY", VALID_API_KEY)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('routers.whatsapp_cloud.get_supabase_client') as mock:
        yield mock


class TestJobCompletionEndpoint:
    """Tests for POST /api/whatsapp/cloud/jobs/{message_id}/complete"""
    
    def test_complete_job_success_delivered(self, mock_env_api_key, mock_supabase):
        """Test successful job completion with 'delivered' status"""
        # Mock Supabase response
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_table = Mock()
        mock_supabase_instance.table.return_value = mock_table
        
        mock_update = Mock()
        mock_table.update.return_value = mock_update
        
        mock_eq = Mock()
        mock_update.eq.return_value = mock_eq
        
        # Mock successful update
        mock_eq.execute.return_value = Mock(data=[{
            "id": TEST_MESSAGE_ID,
            "status": "delivered",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }])
        
        # Make request
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={
                "status": "delivered",
                "result_summary": "Message processed successfully"
            },
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == TEST_MESSAGE_ID
        assert data["status"] == "delivered"
        assert "processed_at" in data
    
    def test_complete_job_success_failed(self, mock_env_api_key, mock_supabase):
        """Test successful job completion with 'failed' status"""
        # Mock Supabase response
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_table = Mock()
        mock_supabase_instance.table.return_value = mock_table
        
        mock_update = Mock()
        mock_table.update.return_value = mock_update
        
        mock_eq = Mock()
        mock_update.eq.return_value = mock_eq
        
        # Mock successful update
        mock_eq.execute.return_value = Mock(data=[{
            "id": TEST_MESSAGE_ID,
            "status": "failed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": "Tally connection failed"
        }])
        
        # Make request
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={
                "status": "failed",
                "error_message": "Tally connection failed"
            },
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == TEST_MESSAGE_ID
        assert data["status"] == "failed"
    
    def test_complete_job_missing_api_key(self, mock_env_api_key):
        """Test that missing API key returns 401"""
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={"status": "delivered"}
            # No X-API-Key header
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API key"
    
    def test_complete_job_invalid_api_key(self, mock_env_api_key):
        """Test that invalid API key returns 401"""
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={"status": "delivered"},
            headers={"X-API-Key": INVALID_API_KEY}
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API key"
    
    def test_complete_job_invalid_status(self, mock_env_api_key):
        """Test that invalid status returns 400"""
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={"status": "pending"},  # Invalid status
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        assert response.status_code == 400
        assert "must be 'delivered' or 'failed'" in response.json()["detail"]
    
    def test_complete_job_failed_without_error(self, mock_env_api_key):
        """Test that 'failed' status without error_message returns 400"""
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={"status": "failed"},  # Missing error_message
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        assert response.status_code == 400
        assert "error_message is required" in response.json()["detail"]
    
    def test_complete_job_not_found(self, mock_env_api_key, mock_supabase):
        """Test that completing non-existent job returns 404"""
        # Mock Supabase response - no data found
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_table = Mock()
        mock_supabase_instance.table.return_value = mock_table
        
        mock_update = Mock()
        mock_table.update.return_value = mock_update
        
        mock_eq = Mock()
        mock_update.eq.return_value = mock_eq
        
        # Mock no data found
        mock_eq.execute.return_value = Mock(data=[])
        
        # Make request
        response = client.post(
            f"/api/whatsapp/cloud/jobs/nonexistent_id/complete",
            json={
                "status": "delivered"
            },
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_complete_job_supabase_error(self, mock_env_api_key, mock_supabase):
        """Test that Supabase errors return 500"""
        # Mock Supabase to raise error
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_table = Mock()
        mock_supabase_instance.table.return_value = mock_table
        
        mock_update = Mock()
        mock_table.update.return_value = mock_update
        
        mock_eq = Mock()
        mock_update.eq.return_value = mock_eq
        
        # Mock Supabase error
        mock_eq.execute.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.post(
            f"/api/whatsapp/cloud/jobs/{TEST_MESSAGE_ID}/complete",
            json={
                "status": "delivered"
            },
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"]["error"] == "COMPLETION_ERROR"


class TestPollingEndpointAuth:
    """Tests for GET /api/whatsapp/cloud/jobs/{tenant_id} authentication"""
    
    def test_poll_jobs_missing_api_key(self, mock_env_api_key):
        """Test that polling without API key returns 401"""
        response = client.get(f"/api/whatsapp/cloud/jobs/{TEST_TENANT_ID}")
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API key"
    
    def test_poll_jobs_invalid_api_key(self, mock_env_api_key):
        """Test that polling with invalid API key returns 401"""
        response = client.get(
            f"/api/whatsapp/cloud/jobs/{TEST_TENANT_ID}",
            headers={"X-API-Key": INVALID_API_KEY}
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API key"
    
    def test_poll_jobs_valid_api_key_no_jobs(self, mock_env_api_key, mock_supabase):
        """Test that polling with valid API key works (empty queue)"""
        # Mock Supabase response - no pending jobs
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_table = Mock()
        mock_supabase_instance.table.return_value = mock_table
        
        mock_select = Mock()
        mock_table.select.return_value = mock_select
        
        mock_eq1 = Mock()
        mock_select.eq.return_value = mock_eq1
        
        mock_eq2 = Mock()
        mock_eq1.eq.return_value = mock_eq2
        
        mock_order = Mock()
        mock_eq2.order.return_value = mock_order
        
        mock_limit = Mock()
        mock_order.limit.return_value = mock_limit
        
        # Mock no pending jobs
        mock_limit.execute.return_value = Mock(data=[])
        
        # Make request
        response = client.get(
            f"/api/whatsapp/cloud/jobs/{TEST_TENANT_ID}",
            headers={"X-API-Key": VALID_API_KEY}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["count"] == 0
        assert data["tenant_id"] == TEST_TENANT_ID
