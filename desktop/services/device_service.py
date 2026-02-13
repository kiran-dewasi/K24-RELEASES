"""
Desktop Device Fingerprinting Service

Generates and persists a stable, unique device identifier for this machine.
Used in the device activation flow to identify the desktop client.
"""

import os
import uuid
import hashlib
import socket
import platform
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_device_fingerprint() -> str:
    """
    Generate a unique device fingerprint based on hardware/OS characteristics.
    
    This fingerprint is stable across reboots and uses:
    - MAC address (via uuid.getnode())
    - Hostname
    - OS platform info
    
    Returns:
        str: SHA256 hash of the combined identifiers (64 characters hex)
    """
    try:
        # Collect hardware/OS identifiers
        mac_address = uuid.getnode()  # Returns MAC as integer
        hostname = socket.gethostname()
        os_platform = platform.platform()
        
        # Combine into a single string
        combined = f"{mac_address}|{hostname}|{os_platform}"
        
        # Hash with SHA256 for privacy and fixed length
        fingerprint = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        logger.debug(f"Generated device fingerprint from: MAC={mac_address}, Host={hostname}, OS={os_platform}")
        return fingerprint
        
    except Exception as e:
        logger.error(f"Error generating device fingerprint: {e}")
        # Fallback to random UUID if hardware detection fails
        fallback = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
        logger.warning(f"Using fallback fingerprint: {fallback}")
        return fallback


def _get_app_data_dir() -> Path:
    """
    Get the K24 application data directory.
    
    On Windows: %APPDATA%/K24
    On Unix-like: ~/.k24
    
    Creates the directory if it doesn't exist.
    
    Returns:
        Path: Application data directory
    """
    # Try to use APPDATA environment variable (Windows)
    appdata = os.environ.get("APPDATA")
    
    if appdata:
        app_dir = Path(appdata) / "K24"
    else:
        # Fallback for Unix-like systems
        app_dir = Path.home() / ".k24"
    
    # Ensure directory exists
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"App data directory: {app_dir}")
    except Exception as e:
        logger.error(f"Failed to create app data directory {app_dir}: {e}")
        # Fallback to temp directory
        import tempfile
        app_dir = Path(tempfile.gettempdir()) / "k24_data"
        app_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback directory: {app_dir}")
    
    return app_dir


def get_or_create_device_id() -> str:
    """
    Get the persisted device ID, or create a new one if it doesn't exist.
    
    The device ID is stored in a JSON file at:
    - Windows: %APPDATA%/K24/device_id.json
    - Unix-like: ~/.k24/device_id.json
    
    File format:
    {
        "device_id": "<sha256_hash>",
        "created_at": "<ISO timestamp>"
    }
    
    Returns:
        str: The device ID (64-character SHA256 hash)
    """
    app_dir = _get_app_data_dir()
    device_file = app_dir / "device_id.json"
    
    # Try to load existing device ID
    if device_file.exists():
        try:
            with open(device_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                device_id = data.get('device_id')
                created_at = data.get('created_at')
                
                if device_id:
                    logger.info(f"✅ Loaded existing device ID from {device_file}")
                    logger.debug(f"Device ID created at: {created_at}")
                    return device_id
                else:
                    logger.warning("device_id.json exists but is missing 'device_id' field")
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse device_id.json: {e}")
        except Exception as e:
            logger.error(f"Failed to read device_id.json: {e}")
    
    # Generate new device ID
    logger.info("🔄 Generating new device ID...")
    device_id = get_device_fingerprint()
    
    # Persist to file
    try:
        data = {
            "device_id": device_id,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        with open(device_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✅ Created and saved new device ID to {device_file}")
        logger.debug(f"Device ID: {device_id[:16]}...{device_id[-8:]}")  # Log partial ID for privacy
        
    except Exception as e:
        logger.error(f"Failed to save device ID to {device_file}: {e}")
        logger.warning("Device ID will not persist across restarts!")
    
    return device_id


def get_device_id() -> str:
    """
    Get the stable device ID for this machine.
    
    This is the main public API for the device service.
    The ID persists across application restarts.
    
    Returns:
        str: The device ID (64-character SHA256 hash)
    """
    return get_or_create_device_id()


# Optional: Regenerate device ID (use with caution!)
def regenerate_device_id() -> str:
    """
    Force regeneration of the device ID.
    
    WARNING: This will invalidate any existing device activations
    using the old device ID. Use only for testing or troubleshooting.
    
    Returns:
        str: The new device ID
    """
    logger.warning("⚠️  Regenerating device ID - this will invalidate existing activations!")
    
    app_dir = _get_app_data_dir()
    device_file = app_dir / "device_id.json"
    
    # Delete existing file if present
    if device_file.exists():
        try:
            device_file.unlink()
            logger.info(f"Deleted existing device_id.json")
        except Exception as e:
            logger.error(f"Failed to delete device_id.json: {e}")
    
    # Generate new ID
    return get_or_create_device_id()


if __name__ == "__main__":
    # Test/debug mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("K24 Device Fingerprinting Service - Test Mode")
    print("=" * 60)
    
    # Test 1: Get device ID (first call)
    print("\n[Test 1] First call to get_device_id():")
    device_id_1 = get_device_id()
    print(f"Device ID: {device_id_1}")
    
    # Test 2: Get device ID again (should be same)
    print("\n[Test 2] Second call to get_device_id() (should be identical):")
    device_id_2 = get_device_id()
    print(f"Device ID: {device_id_2}")
    print(f"IDs match: {device_id_1 == device_id_2} ✅" if device_id_1 == device_id_2 else "IDs match: False ❌")
    
    # Test 3: Show file location
    app_dir = _get_app_data_dir()
    device_file = app_dir / "device_id.json"
    print(f"\n[Test 3] Device ID file location:")
    print(f"Path: {device_file}")
    print(f"Exists: {device_file.exists()}")
    
    if device_file.exists():
        with open(device_file, 'r') as f:
            content = json.load(f)
        print(f"Content: {json.dumps(content, indent=2)}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
