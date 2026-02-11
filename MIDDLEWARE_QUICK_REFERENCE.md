# K24 Middleware - Quick Reference

## 🚀 Quick Start

### Using Middleware in Your Endpoint

```python
from fastapi import Request, Depends
from backend.middleware.main_middleware import RequestOrchestrator

@router.post("/your-endpoint")
async def your_endpoint(
    data: YourModel,
    req: Request,
    current_user: dict = Depends(get_auth_user)
):
    # Run validation pipeline
    await RequestOrchestrator.validate_request(
        request=req,
        user_id=current_user.get("username"),
        user_tier=current_user.get("tier", "free"),
        message_content=data.message  # Optional
    )
    
    # Your logic here...
```

---

## 🔍 Health Check

```bash
# Check system health
curl http://localhost:8001/api/v1/agent/health

# Response
{
  "status": "healthy|degraded",
  "timestamp": "2025-12-03T...",
  "services": {
    "database": {"healthy": true, "message": "Connected"},
    "tally": {"healthy": true, "message": "Connected"},
    "gemini": {"healthy": true, "message": "Authenticated"},
    "redis": {"healthy": true, "message": "Connected"}
  }
}
```

---

## ⚡ Rate Limits

| Type | Limit | Window |
|------|-------|--------|
| Burst | 5/sec | 1 second |
| Global | 100/min | 60 seconds |
| IP | 50/min | 60 seconds |
| User | 20/min | 60 seconds |

---

## 📊 Quotas

| Tier | Daily Limit |
|------|-------------|
| Free | 50 |
| Paid | 1000 |
| Enterprise | ∞ |

---

## 🛡️ Blocked Patterns

### SQL Injection
```
DROP TABLE, DELETE FROM, INSERT INTO, 
UPDATE...SET, UNION SELECT, --, /*, */
```

### Prompt Injection
```
IGNORE PREVIOUS, SYSTEM OVERRIDE, 
ADMIN MODE, DEVELOPER MODE, JAILBREAK
```

---

## 📡 Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `SYSTEM_UNAVAILABLE` | 503 | Services down |
| `BURST_LIMIT_EXCEEDED` | 429 | Too fast |
| `SYSTEM_OVERLOADED` | 429 | Too busy |
| `IP_RATE_LIMITED` | 429 | IP blocked |
| `USER_QUOTA_EXCEEDED` | 429 | User limit |
| `QUOTA_EXCEEDED` | 429 | Daily limit |
| `INJECTION_DETECTED` | 400 | Security threat |
| `INVALID_LENGTH` | 400 | Bad size |
| `INVALID_ENCODING` | 400 | Bad characters |

---

## 🧪 Testing

```bash
# Run unit tests
$env:PYTHONPATH="."; python tests/middleware/test_middleware.py

# With pytest
pytest tests/middleware/test_middleware.py -v
```

---

## ⚙️ Environment Variables

```bash
# Optional: Skip Tally health check
SKIP_TALLY_CHECK=true

# Optional: Enforce Tally connectivity
ENFORCE_TALLY_CHECK=true

# Required: Gemini API key
GOOGLE_API_KEY=your-key-here

# Optional: Custom rate limits
GLOBAL_LIMIT=100
USER_LIMIT=20
IP_LIMIT=50
BURST_LIMIT=5
```

---

## 🔧 Bypass Middleware (for special endpoints)

```python
# Don't run middleware (health check example)
@router.get("/health")
async def health():
    # No middleware runs here
    return {"status": "ok"}
```

---

## 📞 Support

- Documentation: `MIDDLEWARE_DOCUMENTATION.md`
- Implementation Report: `MIDDLEWARE_IMPLEMENTATION_REPORT.md`
- Tests: `tests/middleware/test_middleware.py`

---

**Last Updated**: 2025-12-03
