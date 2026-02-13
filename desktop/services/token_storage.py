"""
Desktop Token Storage Service

Securely stores JWT access and refresh tokens with encryption at rest.
Uses Fernet symmetric encryption with a key derived from the device ID.
"""

import os
import json
import logging
import base64
from pathlib import Path
from typing import Optional, Tuple
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


def _get_app_data_dir() -> Path:
    """
    Get the K24 application data directory.
    
    On Windows: %APPDATA%/K24
    On Unix-like: ~/.k24
    
    Returns:
        Path: Application data directory
    """
    appdata = os.environ.get("APPDATA")
    
    if appdata:
        app_dir = Path(appdata) / "K24"
    else:
        app_dir = Path.home() / ".k24"
    
    # Ensure directory exists
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create app data directory {app_dir}: {e}")
        import tempfile
        app_dir = Path(tempfile.gettempdir()) / "k24_data"
        app_dir.mkdir(parents=True, exist_ok=True)
    
    return app_dir


def _get_encryption_key() -> bytes:
    """
    Derive an encryption key from the device ID.
    
    Uses PBKDF2 with a static salt to derive a Fernet-compatible key.
    The device ID serves as the password, making the encryption
    device-specific.
    
    Returns:
        bytes: 32-byte encryption key for Fernet
    """
    # Import here to avoid circular dependency
    from .device_service import get_device_id
    
    device_id = get_device_id()
    
    # Static salt - not secret, just for key derivation
    # In production, you might want to store this separately
    salt = b"K24_TOKEN_STORAGE_SALT_V1"
    
    # Derive a 32-byte key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(device_id.encode()))
    
    return key


class TokenStorage:
    """
    Secure storage for JWT tokens with encryption at rest.
    
    Tokens are encrypted using Fernet (AES-128 CBC + HMAC) with a key
    derived from the device ID. This ensures tokens are device-specific
    and cannot be copied to another machine.
    """
    
    def __init__(self):
        """Initialize token storage."""
        self.app_dir = _get_app_data_dir()
        self.tokens_file = self.app_dir / "tokens.enc"
        
        try:
            encryption_key = _get_encryption_key()
            self.cipher = Fernet(encryption_key)
            logger.debug("Token storage initialized with encryption")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def save_tokens(self, access_token: str, refresh_token: str) -> None:
        """
        Save access and refresh tokens with encryption.
        
        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token
        """
        try:
            # Prepare data as JSON
            data = {
                "access_token": access_token,
                "refresh_token": refresh_token
            }
            
            # Serialize to JSON bytes
            json_bytes = json.dumps(data).encode('utf-8')
            
            # Encrypt
            encrypted = self.cipher.encrypt(json_bytes)
            
            # Write to file
            with open(self.tokens_file, 'wb') as f:
                f.write(encrypted)
            
            logger.info(f"✅ Tokens saved securely to {self.tokens_file}")
            logger.debug(f"Access token: {access_token[:20]}...")
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            raise
    
    def load_tokens(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Load and decrypt stored tokens.
        
        Returns:
            Tuple of (access_token, refresh_token)
            Returns (None, None) if tokens don't exist or decryption fails
        """
        # Check if file exists
        if not self.tokens_file.exists():
            logger.info("No stored tokens found")
            return (None, None)
        
        try:
            # Read encrypted data
            with open(self.tokens_file, 'rb') as f:
                encrypted = f.read()
            
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted)
            
            # Parse JSON
            data = json.loads(decrypted.decode('utf-8'))
            
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            
            if access_token and refresh_token:
                logger.info("✅ Tokens loaded successfully")
                logger.debug(f"Access token: {access_token[:20]}...")
                return (access_token, refresh_token)
            else:
                logger.warning("Stored tokens are missing fields")
                return (None, None)
                
        except InvalidToken:
            logger.warning("Failed to decrypt tokens - invalid key or corrupted data")
            return (None, None)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse decrypted tokens: {e}")
            return (None, None)
        except Exception as e:
            logger.warning(f"Failed to load tokens: {e}")
            return (None, None)
    
    def clear_tokens(self) -> None:
        """
        Delete stored tokens.
        
        Does not raise exceptions if file doesn't exist.
        """
        try:
            if self.tokens_file.exists():
                self.tokens_file.unlink()
                logger.info(f"✅ Tokens cleared from {self.tokens_file}")
            else:
                logger.debug("No tokens to clear")
                
        except Exception as e:
            logger.error(f"Failed to clear tokens: {e}")
            # Don't raise - clearing is best-effort


# Singleton instance
_token_storage: Optional[TokenStorage] = None


def get_token_storage() -> TokenStorage:
    """
    Get the global TokenStorage instance (singleton).
    
    Returns:
        TokenStorage: The token storage instance
    """
    global _token_storage
    
    if _token_storage is None:
        _token_storage = TokenStorage()
    
    return _token_storage


# Convenience functions
def save_tokens(access_token: str, refresh_token: str) -> None:
    """
    Save tokens using the global storage instance.
    
    Args:
        access_token: JWT access token
        refresh_token: JWT refresh token
    """
    storage = get_token_storage()
    storage.save_tokens(access_token, refresh_token)


def load_tokens() -> Tuple[Optional[str], Optional[str]]:
    """
    Load tokens using the global storage instance.
    
    Returns:
        Tuple of (access_token, refresh_token) or (None, None)
    """
    storage = get_token_storage()
    return storage.load_tokens()


def clear_tokens() -> None:
    """
    Clear tokens using the global storage instance.
    """
    storage = get_token_storage()
    storage.clear_tokens()


if __name__ == "__main__":
    # Test mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("K24 Token Storage Service - Test Mode")
    print("=" * 60)
    
    # Test 1: Save tokens
    print("\n[Test 1] Saving tokens...")
    test_access = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_access"
    test_refresh = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_refresh"
    
    save_tokens(test_access, test_refresh)
    print("✅ Tokens saved")
    
    # Test 2: Load tokens (same process)
    print("\n[Test 2] Loading tokens (same process)...")
    access, refresh = load_tokens()
    
    if access == test_access and refresh == test_refresh:
        print(f"✅ PASS - Tokens match")
        print(f"   Access: {access[:30]}...")
        print(f"   Refresh: {refresh[:30]}...")
    else:
        print(f"❌ FAIL - Tokens don't match")
    
    # Test 3: File location
    storage = get_token_storage()
    print(f"\n[Test 3] Storage location:")
    print(f"   Path: {storage.tokens_file}")
    print(f"   Exists: {storage.tokens_file.exists()}")
    
    if storage.tokens_file.exists():
        size = storage.tokens_file.stat().st_size
        print(f"   Size: {size} bytes (encrypted)")
        
        # Show encrypted content (should be unreadable)
        with open(storage.tokens_file, 'rb') as f:
            encrypted = f.read()
        print(f"   Encrypted data (first 50 bytes): {encrypted[:50]}...")
    
    # Test 4: Clear and verify
    print(f"\n[Test 4] Clearing tokens...")
    clear_tokens()
    
    access, refresh = load_tokens()
    if access is None and refresh is None:
        print("✅ PASS - Tokens cleared successfully")
    else:
        print("❌ FAIL - Tokens still present after clearing")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("Run this script again to test persistence across processes.")
    print("=" * 60)
