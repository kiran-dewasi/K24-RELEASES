"""
Token Refresh Middleware for Desktop Backend

This module provides HTTP client utilities that automatically handle JWT
access token refresh when calling the cloud backend.

Features:
- Loads tokens from token storage automatically
- Detects 401 errors with token expiry
- Calls cloud refresh endpoint to get new tokens
- Updates token storage on successful refresh
- Retries original request with new access token
- Handles refresh failures gracefully

Usage:
    from backend.middleware.auth_client import get_cloud_client
    
    client = get_cloud_client()
    response = client.get("/api/devices/status")
    # Token refresh happens automatically if access token expired
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Cloud API configuration
CLOUD_API_URL = os.getenv("CLOUD_API_URL", "https://api.k24.ai")
DEFAULT_TIMEOUT = 30  # seconds


class CloudAPIClient:
    """
    HTTP client for authenticated calls to the cloud backend.
    
    Automatically handles:
    - Loading tokens from storage
    - Attaching Authorization header
    - Detecting token expiry (401 errors)
    - Refreshing access tokens
    - Retrying failed requests after refresh
    """
    
    def __init__(self, cloud_url: str = CLOUD_API_URL):
        """
        Initialize cloud API client.
        
        Args:
            cloud_url: Base URL of the cloud backend
        """
        self.cloud_url = cloud_url.rstrip("/")
        self.session = self._create_session()
        
        # Import token storage services
        # We import here to avoid circular dependencies
        try:
            from desktop.services.token_storage import load_tokens, save_tokens, clear_tokens
            from desktop.services.device_service import get_device_id
            
            self._load_tokens = load_tokens
            self._save_tokens = save_tokens
            self._clear_tokens = clear_tokens
            self._get_device_id = get_device_id
            
            logger.debug("Token storage services loaded successfully")
        except ImportError as e:
            logger.warning(f"Token storage services not available: {e}")
            # Provide fallback no-op functions
            self._load_tokens = lambda: (None, None)
            self._save_tokens = lambda a, r: None
            self._clear_tokens = lambda: None
            self._get_device_id = lambda: "unknown"
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic.
        
        Retries on:
        - Connection errors
        - Timeouts
        - 429 (Rate limit) - with backoff
        - 500, 502, 503, 504 (Server errors) - with backoff
        
        Does NOT auto-retry on:
        - 401 (handled by token refresh logic)
        - 400, 403, 404 (client errors)
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Max retries
            backoff_factor=1,  # Wait 1s, 2s, 4s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """
        Build authentication headers.
        
        Args:
            access_token: Access token to use (if None, loads from storage)
            
        Returns:
            Dictionary of headers
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "K24-Desktop/1.0"
        }
        
        # Load access token if not provided
        if access_token is None:
            access_token, _ = self._load_tokens()
        
        # Add authorization header if token is available
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        return headers
    
    def _is_token_expired_error(self, response: requests.Response) -> bool:
        """
        Check if the response indicates an expired access token.
        
        Args:
            response: HTTP response from cloud
            
        Returns:
            True if token is expired, False otherwise
        """
        if response.status_code != 401:
            return False
        
        # Check response body for token expiry indicators
        try:
            data = response.json()
            detail = data.get("detail", "").lower()
            error = data.get("error", "").lower()
            
            # Common token expiry messages
            expiry_keywords = [
                "token expired",
                "expired token",
                "token invalid",
                "invalid token",
                "authorization failed",
                "jwt expired"
            ]
            
            for keyword in expiry_keywords:
                if keyword in detail or keyword in error:
                    logger.debug(f"Detected token expiry: {detail or error}")
                    return True
            
        except (ValueError, KeyError):
            pass
        
        # If we get a 401 without specific error, assume token issue
        logger.debug("Detected 401 - treating as potential token expiry")
        return True
    
    def _refresh_tokens(self) -> bool:
        """
        Refresh access token using stored refresh token.
        
        Calls: POST {cloud_url}/api/devices/refresh
        Body: {
            "refresh_token": "<refresh_token>",
            "device_id": "<device_id>"
        }
        
        Returns:
            True if refresh succeeded, False otherwise
        """
        try:
            # Load current tokens
            access_token, refresh_token = self._load_tokens()
            
            if not refresh_token:
                logger.warning("No refresh token available - cannot refresh")
                return False
            
            # Get device ID
            device_id = self._get_device_id()
            
            # Call refresh endpoint
            refresh_url = f"{self.cloud_url}/api/devices/refresh"
            logger.info(f"Refreshing tokens at {refresh_url}")
            
            payload = {
                "refresh_token": refresh_token,
                "device_id": device_id
            }
            
            # Do NOT use self.session here to avoid recursion
            # Also do not attach Authorization header
            response = requests.post(
                refresh_url,
                json=payload,
                timeout=DEFAULT_TIMEOUT,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get("access_token")
                new_refresh_token = data.get("refresh_token")
                
                if not new_access_token or not new_refresh_token:
                    logger.error("Refresh response missing tokens")
                    return False
                
                # Save new tokens
                logger.info("✅ Token refresh successful - updating storage")
                self._save_tokens(new_access_token, new_refresh_token)
                return True
            
            else:
                logger.warning(f"Token refresh failed: {response.status_code}")
                
                # If refresh token is invalid/expired, clear storage
                if response.status_code in (401, 403):
                    logger.warning("Refresh token invalid - clearing tokens")
                    self._clear_tokens()
                
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during token refresh: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}", exc_info=True)
            return False
    
    def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> requests.Response:
        """
        Make an authenticated HTTP request to the cloud backend.
        
        Automatically handles token refresh and retry on 401 errors.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/api/devices/status")
            **kwargs: Additional arguments passed to requests.request()
            
        Returns:
            Response from cloud backend
            
        Raises:
            requests.exceptions.RequestException: On network errors
            requests.exceptions.HTTPError: On HTTP errors (after refresh attempt)
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"
        
        url = f"{self.cloud_url}{path}"
        
        # Load current access token
        access_token, _ = self._load_tokens()
        
        # Build headers
        headers = kwargs.pop("headers", {})
        auth_headers = self._get_auth_headers(access_token)
        headers.update(auth_headers)
        
        # Set default timeout if not provided
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
        
        # Make initial request
        logger.debug(f"{method} {url}")
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            
            # Check if token expired
            if self._is_token_expired_error(response):
                logger.info("Access token expired - attempting refresh")
                
                # Try to refresh tokens
                if self._refresh_tokens():
                    logger.info("Retrying request with new access token")
                    
                    # Reload fresh access token
                    new_access_token, _ = self._load_tokens()
                    
                    # Update headers with new token
                    auth_headers = self._get_auth_headers(new_access_token)
                    headers.update(auth_headers)
                    
                    # Retry the original request
                    response = self.session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        timeout=timeout,
                        **kwargs
                    )
                    
                    logger.info(f"Retry response: {response.status_code}")
                else:
                    logger.error("Token refresh failed - request cannot proceed")
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            raise
    
    # Convenience methods for common HTTP verbs
    
    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request with automatic token refresh"""
        return self.request("GET", path, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        """POST request with automatic token refresh"""
        return self.request("POST", path, **kwargs)
    
    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT request with automatic token refresh"""
        return self.request("PUT", path, **kwargs)
    
    def patch(self, path: str, **kwargs) -> requests.Response:
        """PATCH request with automatic token refresh"""
        return self.request("PATCH", path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request with automatic token refresh"""
        return self.request("DELETE", path, **kwargs)


# Singleton instance
_cloud_client: Optional[CloudAPIClient] = None


def get_cloud_client(cloud_url: str = CLOUD_API_URL) -> CloudAPIClient:
    """
    Get the global CloudAPIClient instance (singleton).
    
    Args:
        cloud_url: Cloud backend URL (only used for first initialization)
        
    Returns:
        CloudAPIClient instance
    """
    global _cloud_client
    
    if _cloud_client is None:
        _cloud_client = CloudAPIClient(cloud_url)
        logger.debug(f"Initialized CloudAPIClient for {cloud_url}")
    
    return _cloud_client


# FastAPI dependency for authenticated cloud calls
def get_authenticated_cloud_client() -> CloudAPIClient:
    """
    FastAPI dependency that provides an authenticated cloud client.
    
    Usage in routes:
        @router.get("/some-route")
        async def some_route(
            cloud_client: CloudAPIClient = Depends(get_authenticated_cloud_client)
        ):
            response = cloud_client.get("/api/devices/status")
            return response.json()
    """
    client = get_cloud_client()
    
    # Check if tokens are available
    access_token, refresh_token = client._load_tokens()
    
    if not access_token and not refresh_token:
        logger.warning("No tokens available for cloud API calls")
        # We don't raise here - let the actual API call fail with proper error
    
    return client
