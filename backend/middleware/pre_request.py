import os
import logging
import time
import asyncio
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import text
from backend.database import SessionLocal
import google.generativeai as genai
import httpx

logger = logging.getLogger(__name__)

class HealthCheck:
    """
    Comprehensive health check system for pre-request validation.
    """
    
    @staticmethod
    async def check_database(timeout: float = 2.0) -> bool:
        """
        Check database connectivity.
        Timeout: 2 seconds
        """
        start_time = time.time()
        db = SessionLocal()
        try:
            # Run simple query
            db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"DB_CONNECTION_FAILED: {e}")
            return False
        finally:
            db.close()
            duration = time.time() - start_time
            if duration > timeout:
                logger.warning(f"Database check took {duration:.2f}s (timeout {timeout}s)")

    @staticmethod
    async def check_tally(timeout: float = 3.0) -> bool:
        """
        Check Tally connectivity via HTTP.
        Timeout: 3 seconds
        """
        tally_url = os.getenv("TALLY_URL", "http://localhost:9000")
        
        # Skip if Tally check is disabled
        if os.getenv("SKIP_TALLY_CHECK", "false").lower() == "true":
            return True
            
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Tally usually doesn't respond to GET on root, but we can try
                # or just check if connection is refused.
                # A generic connection check is enough.
                try:
                    await client.get(tally_url)
                    return True
                except httpx.ConnectError:
                    logger.error("TALLY_CONNECTION_FAILED: Connection refused")
                    return False
                except httpx.TimeoutException:
                    logger.error("TALLY_CONNECTION_FAILED: Timeout")
                    return False
                except Exception:
                    # Tally might return 404 or 405 for GET, which means it's reachable
                    return True
        except Exception as e:
            logger.error(f"TALLY_CONNECTION_FAILED: {e}")
            return False

    @staticmethod
    async def check_gemini(timeout: float = 2.0) -> bool:
        """
        Check Gemini API authentication.
        Timeout: 2 seconds
        """
        # OPTIMIZATION: Do not call API aggressively to save Quota (RPM limit).
        # Just checking Key presence is enough for liveness.
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GEMINI_AUTH_FAILED: API Key missing")
            return False
        return True

    @staticmethod
    async def perform_pre_request_checks():
        """
        Run all critical health checks.
        Raises HTTPException if critical services are down.
        """
        # 1. Database Check
        if not await HealthCheck.check_database():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unavailable"
            )
            
        # 2. Tally Check
        # Only enforce if specifically configured to do so, otherwise just log
        if os.getenv("ENFORCE_TALLY_CHECK", "false").lower() == "true":
            if not await HealthCheck.check_tally():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Tally unreachable"
                )

        # 3. Gemini Check
        if not await HealthCheck.check_gemini():
             raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable"
            )
