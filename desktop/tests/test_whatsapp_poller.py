"""
Tests for WhatsApp Poller Service
"""

import pytest

pytest_plugins = ('pytest_asyncio',)
asyncio_default_fixture_loop_scope = 'function'


import asyncio
from unittest.mock import Mock, patch, AsyncMock
from desktop.services.whatsapp_poller import WhatsAppPoller


@pytest.fixture
def poller():
    """Create a WhatsAppPoller instance for testing"""
    return WhatsAppPoller(tenant_id="TEST_TENANT", api_key="test_api_key_123")


@pytest.mark.asyncio
async def test_poll_once_success(poller):
    """Test successful polling returns jobs"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "job_1",
            "tenant_id": "TEST_TENANT",
            "message_text": "Test message 1",
            "customer_phone": "+1234567890"
        },
        {
            "id": "job_2", 
            "tenant_id": "TEST_TENANT",
            "message_text": "Test message 2",
            "customer_phone": "+1234567891"
        }
    ]
    mock_response.raise_for_status = Mock()
    
    with patch.object(poller.session, 'get', return_value=mock_response):
        jobs = await poller.poll_once()
    
    assert len(jobs) == 2
    assert jobs[0]["id"] == "job_1"
    assert jobs[1]["message_text"] == "Test message 2"
    assert poller.stats["total_polls"] == 1


@pytest.mark.asyncio
async def test_poll_once_401_error(poller):
    """Test polling handles 401 authentication errors"""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
    
    # Mock the HTTPError properly
    from requests.exceptions import HTTPError
    error = HTTPError()
    error.response = mock_response
    
    with patch.object(poller.session, 'get', side_effect=error):
        jobs = await poller.poll_once()
    
    assert len(jobs) == 0
    assert poller.stats["last_error"] == "Invalid API key"


@pytest.mark.asyncio
async def test_poll_once_429_rate_limit(poller):
    """Test polling handles 429 rate limit errors"""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")
    
    from requests.exceptions import HTTPError
    error = HTTPError()
    error.response = mock_response
    
    with patch.object(poller.session, 'get', side_effect=error):
        jobs = await poller.poll_once()
    
    assert len(jobs) == 0
    assert poller.stats["last_error"] == "Rate limited"


@pytest.mark.asyncio
async def test_process_job_success(poller):
    """Test job processing marks job as complete"""
    job = {
        "id": "job_123",
        "message_text": "Create sales voucher",
        "customer_phone": "+1234567890"
    }
    
    mock_complete_response = Mock()
    mock_complete_response.status_code = 200
    mock_complete_response.raise_for_status = Mock()
    
    with patch.object(poller.session, 'post', return_value=mock_complete_response) as mock_post:
        await poller.process_job(job)
    
    # Verify completion was called
    assert mock_post.called
    call_args = mock_post.call_args
    assert "job_123/complete" in call_args[0][0]
    assert call_args[1]["json"]["status"] == "delivered"
    
    # Verify stats updated
    assert poller.stats["successful_jobs"] == 1
    assert poller.stats["total_jobs"] == 1


@pytest.mark.asyncio
async def test_get_stats(poller):
    """Test stats reporting"""
    poller.stats["total_jobs"] = 10
    poller.stats["successful_jobs"] = 8
    poller.stats["failed_jobs"] = 2
    
    stats = poller.get_stats()
    
    assert stats["total_jobs"] == 10
    assert stats["successful_jobs"] == 8
    assert stats["failed_jobs"] == 2
    assert stats["success_rate"] == 80.0
    assert stats["tenant_id"] == "TEST_TENANT"
    assert stats["is_running"] == False


@pytest.mark.asyncio
async def test_session_has_correct_headers(poller):
    """Test session is configured with correct headers"""
    assert poller.session.headers["X-API-Key"] == "test_api_key_123"
    assert poller.session.headers["Content-Type"] == "application/json"


def test_init_poller_missing_env_vars():
    """Test init_poller raises error when env vars missing"""
    import os
    from desktop.services.whatsapp_poller import init_poller
    
    # Clear env vars
    old_tenant = os.environ.get("TENANT_ID")
    old_api_key = os.environ.get("DESKTOP_API_KEY")
    
    if "TENANT_ID" in os.environ:
        del os.environ["TENANT_ID"]
    if "DESKTOP_API_KEY" in os.environ:
        del os.environ["DESKTOP_API_KEY"]
    
    try:
        with pytest.raises(ValueError, match="TENANT_ID"):
            init_poller()
    finally:
        # Restore env vars
        if old_tenant:
            os.environ["TENANT_ID"] = old_tenant
        if old_api_key:
            os.environ["DESKTOP_API_KEY"] = old_api_key
