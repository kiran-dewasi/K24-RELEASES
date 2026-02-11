"""
Supabase Client for K24 Cloud Backend

Provides authenticated Supabase connection for cloud services.
Uses service role key for server-side operations.
"""
import os
from supabase import create_client, Client
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance (singleton pattern)

    Returns:
        Client: Authenticated Supabase client

    Raises:
        ValueError: If required environment variables are not set
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Service role for server-side

    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
        )

    logger.info(f"Initializing Supabase client: {supabase_url}")
    _supabase_client = create_client(supabase_url, supabase_key)

    return _supabase_client


def reset_client():
    """Reset the client instance (useful for testing)"""
    global _supabase_client
    _supabase_client = None
