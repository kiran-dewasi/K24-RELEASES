"""
Configuration Service for K24 Desktop Backend.

Centralizes access to:
- Cloud Backend URL (e.g., https://api.k24.ai or localhost)
- API Keys for Machine-to-Machine communication (e.g., WhatsApp Poller)
- Session Tokens for Desktop Frontend authentication

Loads configuration from:
1. Environment Variables (Highest Priority)
2. backend/config/cloud.json (Packaged with Installer)
3. Hardcoded Defaults (Lowest Priority)

Usage:
    from backend.services.config_service import get_cloud_url, get_desktop_api_key

    url = get_cloud_url()
    api_key = get_desktop_api_key()
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CLOUD_URL = "https://api.k24.ai"
CONFIG_FILE_PATH = Path(__file__).parent.parent / "config" / "cloud.json"


def _load_config_file() -> Dict:
    """Load configuration from JSON file."""
    if not CONFIG_FILE_PATH.exists():
        logger.warning(f"Config file not found at {CONFIG_FILE_PATH}")
        return {}
    
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return {}


# Cache configuration
_config_cache = _load_config_file()


def get_cloud_url() -> str:
    """
    Get the Cloud Backend URL.
    
    Priority:
    1. CLOUD_API_URL env var
    2. 'cloud_api_url' in config.json
    3. Hardcoded default
    """
    url = os.getenv("CLOUD_API_URL")
    if url:
        return url.rstrip("/")
    
    url = _config_cache.get("cloud_api_url")
    if url:
        return url.rstrip("/")
        
    return DEFAULT_CLOUD_URL


def get_desktop_api_key() -> Optional[str]:
    """
    Get the API Key for desktop-to-cloud machine authentication.
    Used by WhatsApp Poller to fetch jobs.
    
    Source:
    - DESKTOP_API_KEY env var (Secure, set by installer or user)
    - Windows Credentials Manager (Future implementation)
    """
    key = os.getenv("DESKTOP_API_KEY")
    if not key:
        # Check config for backup location or static key (unlikely for production)
        key = _config_cache.get("desktop_api_key")
        
    if not key:
        logger.warning("DESKTOP_API_KEY is not set. Cloud polling may fail.")
        
    return key


def get_tenant_id() -> Optional[str]:
    """
    Get the Tenant ID for the current desktop installation.
    
    Retrieved from secure token storage where it was saved during activation.
    Required for polling tenant-specific jobs.
    """
    try:
        from desktop.services.token_storage import get_stored_tenant_id
        return get_stored_tenant_id()
    except ImportError:
        logger.warning("Could not import token_storage service")
        return None
    except Exception as e:
        logger.error(f"Failed to get tenant_id: {e}")
        return None


def get_environment() -> str:
    """Get current environment name (production, development, staging)."""
    return os.getenv("ENV", _config_cache.get("environment", "production"))


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment().lower() == "production"

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    print(f"Cloud URL: {get_cloud_url()}")
    print(f"Environment: {get_environment()}")
    print(f"API Key Set: {'Yes' if get_desktop_api_key() else 'No'}")
