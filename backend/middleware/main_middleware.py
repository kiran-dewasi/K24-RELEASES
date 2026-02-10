import logging
import time
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status, Depends
from backend.middleware.health_check import HealthCheck
from backend.middleware.rate_limiting import rate_limiter
from backend.middleware.message_validation import MessageValidator
from backend.middleware.quota_tracking import quota_tracker

logger = logging.getLogger(__name__)

class RequestOrchestrator:
    """
    Main middleware orchestrator that runs the pre-request pipeline:
    1. Health Checks
    2. Message Validation
    3. Rate Limiting
    4. Quota Tracking
    """
    
    @staticmethod
    async def validate_request(
        request: Request,
        user_id: Optional[str] = None,
        user_tier: str = "free",
        message_content: Optional[str] = None
    ):
        """
        Run the full validation pipeline.
        Raises HTTPException on failure.
        """
        
        # 1. Health Checks
        # We run this first to fail fast if system is down
        checks = await HealthCheck.perform_all_checks()
        if not checks["overall_healthy"]:
            # Construct detailed error
            failed_services = [k for k, v in checks.items() if k != "overall_healthy" and not v["healthy"]]
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": True,
                    "error_code": "SYSTEM_UNAVAILABLE",
                    "message": f"Critical services unavailable: {', '.join(failed_services)}",
                    "details": checks
                }
            )

        # 2. Message Validation (if content provided)
        if message_content:
            is_valid, err_code, err_msg = MessageValidator.validate_message(message_content)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": True,
                        "error_code": err_code,
                        "message": err_msg
                    }
                )

        # 3. Rate Limiting
        # Checks global, IP, and user limits
        await rate_limiter.check_limits(request, user_id)

        # 4. Quota Tracking (if authenticated)
        if user_id:
            allowed, remaining, limit = quota_tracker.check_and_increment(user_id, user_tier)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": True,
                        "error_code": "QUOTA_EXCEEDED",
                        "message": "Daily request quota exceeded.",
                        "details": {
                            "limit": limit,
                            "reset_in": "Midnight UTC"
                        }
                    }
                )
            
            # Attach quota info to request state for logging/headers if needed
            request.state.quota_remaining = remaining

        return True
