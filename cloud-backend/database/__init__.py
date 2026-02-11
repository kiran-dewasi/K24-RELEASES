"""
Cloud Backend Database Module

Provides Supabase client and database utilities for cloud services.
"""
from .supabase_client import get_supabase_client, reset_client

__all__ = ["get_supabase_client", "reset_client"]
