import time
import logging
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException, status
from collections import defaultdict

logger = logging.getLogger(__name__)

# Constants
GLOBAL_LIMIT = 100  # requests per minute
USER_LIMIT = 20     # requests per minute
IP_LIMIT = 50       # requests per minute
BURST_LIMIT = 5     # requests per second

class RateLimiter:
    """
    Rate limiting logic with Redis support and in-memory fallback.
    Implements Token Bucket / Fixed Window algorithm.
    """
    
    def __init__(self):
        # In-memory storage: {key: [timestamps]}
        self._memory_store: Dict[str, list] = defaultdict(list)
        self._use_redis = False
        # Try to initialize Redis
        try:
            # import redis
            # self.redis = redis.Redis(...)
            # self._use_redis = True
            pass
        except:
            pass

    def _clean_old_requests(self, key: str, window: int):
        """Remove requests older than window seconds"""
        now = time.time()
        self._memory_store[key] = [t for t in self._memory_store[key] if now - t < window]

    def is_allowed(self, key: str, limit: int, window: int = 60) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed.
        Returns: (allowed, retry_after)
        """
        now = time.time()
        
        if self._use_redis:
            # Redis implementation placeholder
            return True, None
        else:
            # In-memory implementation
            self._clean_old_requests(key, window)
            current_count = len(self._memory_store[key])
            
            if current_count >= limit:
                # Calculate retry after
                oldest = self._memory_store[key][0] if self._memory_store[key] else now
                retry_after = int(window - (now - oldest))
                return False, max(1, retry_after)
            
            self._memory_store[key].append(now)
            return True, None

    async def check_limits(self, request: Request, user_id: Optional[str] = None):
        """
        Check all rate limits for a request.
        Raises HTTPException if limit exceeded.
        """
        client_ip = request.client.host if request.client else "unknown"
        
        # 1. Burst Limit (per IP, 1 second window)
        allowed, retry = self.is_allowed(f"burst:{client_ip}", BURST_LIMIT, window=1)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": True,
                    "error_code": "BURST_LIMIT_EXCEEDED",
                    "message": "Too many requests. Slow down.",
                    "retry_after": retry
                }
            )

        # 2. Global Limit (1 minute window)
        allowed, retry = self.is_allowed("global", GLOBAL_LIMIT, window=60)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": True,
                    "error_code": "SYSTEM_OVERLOADED",
                    "message": "System is busy. Please try again later.",
                    "retry_after": retry
                }
            )

        # 3. IP Limit (1 minute window)
        allowed, retry = self.is_allowed(f"ip:{client_ip}", IP_LIMIT, window=60)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": True,
                    "error_code": "IP_RATE_LIMITED",
                    "message": "Too many requests from this IP.",
                    "retry_after": retry
                }
            )

        # 4. User Limit (if authenticated)
        if user_id:
            allowed, retry = self.is_allowed(f"user:{user_id}", USER_LIMIT, window=60)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": True,
                        "error_code": "USER_QUOTA_EXCEEDED",
                        "message": "User rate limit exceeded.",
                        "retry_after": retry
                    }
                )

# Global instance
rate_limiter = RateLimiter()
