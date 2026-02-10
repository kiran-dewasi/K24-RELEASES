from cryptography.fernet import Fernet
import base64
import hashlib
import platform
import os
import logging

logger = logging.getLogger(__name__)

class DataEncryption:
    def __init__(self):
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """
        Create cipher from machine-specific key.
        This ensures the encryption key is bound to the hardware and not stored in code.
        """
        try:
            # Gather machine-specific identifiers
            node = platform.node()
            machine = platform.machine()
            system = platform.system()
            
            # Additional entropy from user profile if available, else just system
            # Using only system derived values ensures stability across app restarts on same machine
            machine_id = f"{node}|{machine}|{system}"
            
            # Create a 32-byte key
            key = hashlib.sha256(machine_id.encode()).digest()
            encoded_key = base64.urlsafe_b64encode(key)
            
            return Fernet(encoded_key)
        except Exception as e:
            logger.error(f"Failed to generate encryption key: {e}")
            # Fallback for dev environments where platform info might be shaky (rare)
            # THIS IS A FALLBACK ONLY - IN PROD HARDWARE BINDING IS KEY
            fallback = hashlib.sha256(b"k24-fallback-key").digest()
            return Fernet(base64.urlsafe_b64encode(fallback))
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive string"""
        if not data:
            return data
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise e
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string"""
        if not encrypted_data:
            return encrypted_data
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise e

# Global encryptor instance
encryptor = DataEncryption()
