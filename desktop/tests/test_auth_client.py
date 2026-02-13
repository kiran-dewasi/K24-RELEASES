"""
Tests for Token Refresh Middleware (auth_client)

Validates:
1. Token loading and header attachment
2. Token expiry detection
3. Automatic token refresh
4. Request retry after refresh
5. Graceful handling of refresh failures
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from backend.middleware.auth_client import CloudAPIClient, get_cloud_client


class TestCloudAPIClient:
    """Test CloudAPIClient token refresh behavior"""
    
    @pytest.fixture
    def mock_token_storage(self):
        """Mock token storage services"""
        with patch('backend.middleware.auth_client.CloudAPIClient._load_tokens') as load, \
             patch('backend.middleware.auth_client.CloudAPIClient._save_tokens') as save, \
             patch('backend.middleware.auth_client.CloudAPIClient._clear_tokens') as clear, \
             patch('backend.middleware.auth_client.CloudAPIClient._get_device_id') as device_id:
            
            # Set initial tokens
            load.return_value = ("test_access_token", "test_refresh_token")
            device_id.return_value = "test_device_123"
            
            yield {
                'load': load,
                'save': save,
                'clear': clear,
                'device_id': device_id
            }
    
    @pytest.fixture
    def client(self, mock_token_storage):
        """Create CloudAPIClient instance with mocked storage"""
        return CloudAPIClient(cloud_url="https://test-api.example.com")
    
    def test_auth_headers_with_token(self, client):
        """Test that Authorization header is added when token is present"""
        headers = client._get_auth_headers("my_access_token")
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my_access_token"
        assert headers["Content-Type"] == "application/json"
    
    def test_auth_headers_without_token(self, client):
        """Test headers when no token is provided"""
        with patch.object(client, '_load_tokens', return_value=(None, None)):
            headers = client._get_auth_headers()
            
            assert "Authorization" not in headers
            assert headers["Content-Type"] == "application/json"
    
    def test_token_expired_detection(self, client):
        """Test detection of 401 token expiry errors"""
        # Create mock response with token expiry
        response = Mock()
        response.status_code = 401
        response.json.return_value = {
            "detail": "Token expired",
            "error": "invalid_token"
        }
        
        assert client._is_token_expired_error(response) == True
    
    def test_non_401_not_expired(self, client):
        """Test that non-401 errors are not treated as token expiry"""
        response = Mock()
        response.status_code = 403
        
        assert client._is_token_expired_error(response) == False
    
    @patch('requests.post')
    def test_successful_token_refresh(self, mock_post, client):
        """Test successful token refresh flow"""
        # Mock refresh endpoint response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        }
        mock_post.return_value = mock_response
        
        # Call refresh
        result = client._refresh_tokens()
        
        # Verify success
        assert result == True
        
        # Verify refresh endpoint was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/api/devices/refresh" in call_args[0][0]
        
        # Verify new tokens were saved
        client._save_tokens.assert_called_once_with(
            "new_access_token",
            "new_refresh_token"
        )
    
    @patch('requests.post')
    def test_failed_token_refresh(self, mock_post, client):
        """Test handling of failed token refresh"""
        # Mock refresh endpoint failure
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        # Call refresh
        result = client._refresh_tokens()
        
        # Verify failure
        assert result == False
        
        # Verify tokens were cleared
        client._clear_tokens.assert_called_once()
    
    @patch('requests.Session.request')
    def test_request_with_valid_token(self, mock_request, client):
        """Test normal request with valid token (no refresh needed)"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_request.return_value = mock_response
        
        # Make request
        response = client.get("/api/devices/status")
        
        # Verify success
        assert response.status_code == 200
        
        # Verify only one request was made (no retry)
        assert mock_request.call_count == 1
        
        # Verify Authorization header was sent
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        assert "Authorization" in headers
        assert "Bearer test_access_token" in headers["Authorization"]
    
    @patch('requests.post')  # For refresh
    @patch('requests.Session.request')  # For main request
    def test_request_with_expired_token_and_successful_refresh(
        self, mock_request, mock_refresh_post, client
    ):
        """Test automatic token refresh and retry on 401"""
        # First request fails with 401
        expired_response = Mock()
        expired_response.status_code = 401
        expired_response.json.return_value = {"detail": "Token expired"}
        
        # Second request (after refresh) succeeds
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"status": "ok"}
        
        # Configure mock to return expired first, then success
        mock_request.side_effect = [expired_response, success_response]
        
        # Mock successful refresh
        refresh_response = Mock()
        refresh_response.status_code = 200
        refresh_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        }
        mock_refresh_post.return_value = refresh_response
        
        # Make request
        response = client.get("/api/devices/status")
        
        # Verify final response is successful
        assert response.status_code == 200
        
        # Verify request was made twice (initial + retry)
        assert mock_request.call_count == 2
        
        # Verify refresh was called
        assert mock_refresh_post.call_count == 1
        
        # Verify new tokens were saved
        client._save_tokens.assert_called_once_with(
            "new_access_token",
            "new_refresh_token"
        )
    
    @patch('requests.post')  # For refresh
    @patch('requests.Session.request')  # For main request
    def test_request_with_expired_token_and_failed_refresh(
        self, mock_request, mock_refresh_post, client
    ):
        """Test handling when both access and refresh tokens are invalid"""
        # First request fails with 401
        expired_response = Mock()
        expired_response.status_code = 401
        expired_response.json.return_value = {"detail": "Token expired"}
        mock_request.return_value = expired_response
        
        # Refresh also fails
        refresh_fail_response = Mock()
        refresh_fail_response.status_code = 401
        mock_refresh_post.return_value = refresh_fail_response
        
        # Make request
        response = client.get("/api/devices/status")
        
        # Verify final response is still 401
        assert response.status_code == 401
        
        # Verify tokens were cleared
        client._clear_tokens.assert_called_once()
    
    def test_convenience_methods(self, client):
        """Test GET, POST, PUT, etc. convenience methods"""
        with patch.object(client, 'request') as mock_request:
            mock_request.return_value = Mock(status_code=200)
            
            # Test each HTTP method
            client.get("/test")
            mock_request.assert_called_with("GET", "/test")
            
            client.post("/test", json={"data": "value"})
            mock_request.assert_called_with("POST", "/test", json={"data": "value"})
            
            client.put("/test")
            mock_request.assert_called_with("PUT", "/test")
            
            client.patch("/test")
            mock_request.assert_called_with("PATCH", "/test")
            
            client.delete("/test")
            mock_request.assert_called_with("DELETE", "/test")
    
    def test_singleton_pattern(self):
        """Test that get_cloud_client returns singleton instance"""
        client1 = get_cloud_client()
        client2 = get_cloud_client()
        
        assert client1 is client2


# Integration test scenarios
class TestTokenRefreshIntegration:
    """
    Integration test scenarios (would require actual cloud backend)
    These are templates for manual testing.
    """
    
    def test_scenario_1_valid_tokens(self):
        """
        Scenario: Desktop has valid tokens in storage
        
        Steps:
        1. Ensure tokens.enc exists with valid access/refresh tokens
        2. Make API call via CloudAPIClient
        3. Verify: Request succeeds without refresh
        """
        pass
    
    def test_scenario_2_expired_access_token(self):
        """
        Scenario: Access token expired but refresh token valid
        
        Steps:
        1. Store tokens where access_token is expired
        2. Make API call via CloudAPIClient
        3. Verify: 
           - Cloud returns 401 on first request
           - Client calls refresh endpoint
           - New tokens are stored
           - Original request is retried and succeeds
        """
        pass
    
    def test_scenario_3_both_tokens_expired(self):
        """
        Scenario: Both access and refresh tokens expired
        
        Steps:
        1. Store expired tokens
        2. Make API call via CloudAPIClient
        3. Verify:
           - Cloud returns 401 on first request
           - Refresh endpoint returns 401
           - Tokens are cleared from storage
           - Final response is 401 with clear error
        """
        pass


if __name__ == "__main__":
    print("Running token refresh middleware tests...")
    print("\nTo run with pytest:")
    print("  pytest desktop/tests/test_auth_client.py -v")
    print("\nFor coverage:")
    print("  pytest desktop/tests/test_auth_client.py --cov=backend.middleware.auth_client")
