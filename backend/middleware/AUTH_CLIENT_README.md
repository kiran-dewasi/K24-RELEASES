# Token Refresh Middleware - Usage Guide

## Overview

The `CloudAPIClient` middleware provides automatic JWT access token refresh for desktop backend calls to the cloud API. When an access token expires, the client automatically:

1. Detects the 401 error
2. Calls the refresh endpoint with the stored refresh token
3. Updates the stored tokens
4. Retries the original request
5. Returns the result transparently

## Quick Start

### Basic Usage

```python
from backend.middleware.auth_client import get_cloud_client

# Get the singleton client instance
client = get_cloud_client()

# Make authenticated requests - token refresh happens automatically
response = client.get("/api/devices/status")

if response.status_code == 200:
    data = response.json()
    print(f"Device status: {data}")
```

### Using as FastAPI Dependency

```python
from fastapi import APIRouter, Depends
from backend.middleware.auth_client import CloudAPIClient, get_authenticated_cloud_client

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(
    cloud_client: CloudAPIClient = Depends(get_authenticated_cloud_client)
):
    """
    Example endpoint that calls the cloud backend.
    Token refresh is automatic.
    """
    response = cloud_client.get("/api/devices/me")
    
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail="Cloud API error"
        )
```

## API Reference

### CloudAPIClient Class

The main HTTP client class that wraps `requests.Session` with token refresh logic.

#### Methods

##### `get(path, **kwargs)`
Make a GET request to the cloud backend.

```python
response = client.get("/api/devices/status")
```

##### `post(path, **kwargs)`
Make a POST request to the cloud backend.

```python
response = client.post("/api/devices/refresh", json={
    "refresh_token": "...",
    "device_id": "..."
})
```

##### `put(path, **kwargs)`, `patch(path, **kwargs)`, `delete(path, **kwargs)`
Other HTTP verbs work the same way.

##### `request(method, path, **kwargs)`
Low-level request method. Use verb methods instead for convenience.

### Functions

##### `get_cloud_client(cloud_url=CLOUD_API_URL) -> CloudAPIClient`
Returns the singleton `CloudAPIClient` instance.

```python
from backend.middleware.auth_client import get_cloud_client

client = get_cloud_client()
# or with custom URL
client = get_cloud_client("https://custom-api.example.com")
```

##### `get_authenticated_cloud_client() -> CloudAPIClient`
FastAPI dependency that provides an authenticated cloud client.

```python
from fastapi import Depends
from backend.middleware.auth_client import get_authenticated_cloud_client, CloudAPIClient

@app.get("/endpoint")
async def endpoint(client: CloudAPIClient = Depends(get_authenticated_cloud_client)):
    response = client.get("/api/data")
    return response.json()
```

## Token Refresh Flow

### Success Scenario

```
1. Desktop makes request: GET /api/devices/status
   ├─ Loads access_token from storage
   └─ Adds header: Authorization: Bearer <access_token>

2. Cloud responds: 401 - Token expired

3. Middleware detects token expiry
   └─ Calls: POST /api/devices/refresh
      ├─ Body: { "refresh_token": "...", "device_id": "..." }
      └─ Response: { "access_token": "new_token", "refresh_token": "new_refresh" }

4. Middleware updates token storage
   └─ save_tokens(new_access_token, new_refresh_token)

5. Middleware retries original request
   └─ GET /api/devices/status (with new token)

6. Cloud responds: 200 OK

7. Original caller receives successful response
   └─ Transparent! No error seen by caller
```

### Failure Scenario (Refresh Token Also Expired)

```
1. Desktop makes request: GET /api/devices/status
   └─ Access token expired

2. Cloud responds: 401

3. Middleware tries to refresh
   └─ POST /api/devices/refresh
      └─ Response: 401 - Refresh token also invalid

4. Middleware clears stored tokens
   └─ clear_tokens()

5. Original request returns 401
   └─ Caller sees auth error and can prompt re-activation
```

## Configuration

### Environment Variables

- `CLOUD_API_URL` - Base URL of the cloud backend (default: `https://api.k24.ai`)

### Token Storage

The client uses `desktop.services.token_storage` to load and save tokens:

- `load_tokens()` - Returns `(access_token, refresh_token)` tuple
- `save_tokens(access, refresh)` - Stores new tokens securely
- `clear_tokens()` - Clears stored tokens

### Device ID

The client uses `desktop.services.device_service.get_device_id()` to get the device fingerprint for refresh requests.

## Error Handling

### Network Errors

```python
try:
    response = client.get("/api/data")
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    logger.error(f"Network error: {e}")
    # Handle connection failures, timeouts, etc.
```

### Token Expiry

Token expiry is handled automatically. You only need to handle the case where **both** access and refresh tokens are invalid:

```python
response = client.get("/api/data")

if response.status_code == 401:
    # Both tokens expired - user needs to re-activate
    return {
        "error": "authentication_required",
        "message": "Please re-activate this device"
    }
```

### Cloud API Errors

```python
response = client.get("/api/data")

if response.status_code == 200:
    return response.json()
elif response.status_code == 401:
    # Auth failed (even after refresh attempt)
    raise HTTPException(401, "Authentication required")
elif response.status_code == 403:
    # Permission denied
    raise HTTPException(403, "Access denied")
elif response.status_code >= 500:
    # Cloud backend error
    raise HTTPException(503, "Cloud service unavailable")
```

## Testing

### Running Unit Tests

```bash
pytest desktop/tests/test_auth_client.py -v
```

### Testing with Coverage

```bash
pytest desktop/tests/test_auth_client.py --cov=backend.middleware.auth_client --cov-report=html
```

### Manual Testing Scenarios

#### Scenario 1: Valid Tokens
1. Ensure `tokens.enc` exists with valid tokens
2. Make a cloud API call via CloudAPIClient
3. ✅ Request should succeed without refresh

#### Scenario 2: Expired Access Token
1. Store tokens with expired access_token
2. Make a cloud API call
3. ✅ Request should:
   - Get 401 on first attempt
   - Call refresh endpoint
   - Save new tokens
   - Retry and succeed

#### Scenario 3: Both Tokens Expired
1. Store completely expired tokens
2. Make a cloud API call
3. ✅ Request should:
   - Get 401 on first attempt
   - Try refresh, get 401
   - Clear stored tokens
   - Return 401 to caller

## Examples

### Example 1: Check Device Status

```python
from backend.middleware.auth_client import get_cloud_client
import logging

logger = logging.getLogger(__name__)

def check_device_status():
    """Check device status with automatic token refresh"""
    try:
        client = get_cloud_client()
        response = client.get("/api/devices/me")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Device status: {data.get('status')}")
            return data
        elif response.status_code == 401:
            logger.warning("Authentication failed - device needs re-activation")
            return None
        else:
            logger.error(f"Unexpected error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to check device status: {e}")
        return None
```

### Example 2: Polling for Jobs

```python
from backend.middleware.auth_client import get_cloud_client
import time

class WhatsAppPoller:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.client = get_cloud_client()
    
    def poll_jobs(self):
        """Fetch pending jobs from cloud"""
        try:
            response = self.client.get(
                f"/api/whatsapp/cloud/jobs/{self.tenant_id}",
                params={"limit": 10}
            )
            
            if response.status_code == 200:
                jobs = response.json()
                return jobs.get("jobs", [])
            elif response.status_code == 401:
                # Refresh failed - stop polling
                logger.error("Authentication failed - stopping poller")
                return []
            else:
                logger.warning(f"Polling failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Polling error: {e}")
            return []
    
    def start_polling(self):
        """Poll for jobs every 10 seconds"""
        while True:
            jobs = self.poll_jobs()
            
            for job in jobs:
                self.process_job(job)
            
            time.sleep(10)
```

### Example 3: Complete Job

```python
def complete_job(job_id, status, error_message=None):
    """Mark a job as complete"""
    client = get_cloud_client()
    
    response = client.post(
        f"/api/whatsapp/cloud/jobs/{job_id}/complete",
        json={
            "status": status,
            "error_message": error_message
        }
    )
    
    if response.status_code == 200:
        logger.info(f"Job {job_id} completed successfully")
        return True
    else:
        logger.error(f"Failed to complete job: {response.status_code}")
        return False
```

## Troubleshooting

### Issue: Tokens not loading

**Symptom**: Every request fails with 401, no refresh attempt

**Cause**: Token storage is empty or corrupted

**Solution**:
1. Check if `%APPDATA%/K24/tokens.enc` exists
2. Verify device activation completed successfully
3. Re-activate device if needed

### Issue: Infinite refresh loop

**Symptom**: Constant refresh calls, requests never succeed

**Cause**: Refresh endpoint returning invalid tokens

**Solution**:
1. Check cloud backend logs for refresh endpoint errors
2. Verify device_id matches what's stored in cloud
3. Clear tokens and re-activate: `clear_tokens()`

### Issue: Network timeouts

**Symptom**: Requests hang or timeout frequently

**Cause**: Network connectivity issues or cloud backend down

**Solution**:
1. Check network connectivity
2. Verify cloud backend is responding: `curl https://api.k24.ai/health`
3. Adjust timeout in client creation if needed

## Best Practices

### 1. Use the Singleton

Always use `get_cloud_client()` instead of creating new instances:

```python
# ✅ Good
client = get_cloud_client()

# ❌ Bad - creates multiple sessions
client = CloudAPIClient()
```

### 2. Check Response Status

Always check the status code before parsing JSON:

```python
# ✅ Good
response = client.get("/api/data")
if response.status_code == 200:
    data = response.json()

# ❌ Bad - may crash on error responses
data = client.get("/api/data").json()
```

### 3. Handle Auth Failures

Even with auto-refresh, both tokens can expire:

```python
# ✅ Good
response = client.get("/api/data")
if response.status_code == 401:
    prompt_user_to_reactivate()

# ❌ Bad - assumes requests always succeed
data = client.get("/api/data").json()
```

### 4. Log Errors

Always log errors for debugging:

```python
# ✅ Good
try:
    response = client.get("/api/data")
except Exception as e:
    logger.error(f"Request failed: {e}", exc_info=True)

# ❌ Bad - silent failures
try:
    response = client.get("/api/data")
except:
    pass
```

## See Also

- `desktop/services/token_storage.py` - Token encryption and storage
- `desktop/services/device_service.py` - Device fingerprinting
- `backend/routers/devices.py` - Device activation endpoint
- `plan.md` - M3 T5 for implementation details
