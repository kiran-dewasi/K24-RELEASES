import hashlib
import platform
import uuid
import json
import base64
import os
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# PRODUCTION PUBLIC KEY (Hardcoded to prevent tampering)
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxWVFYF7jsQi+z8W+5FZX
5Y5Uw0JZLk/Yn/QkMAgGB7gKDSz8nrH6DZEGGu35gsvHzHut5XI44Yr+mmE8dPGl
2PDdVWEJkB+YjvUGDW6KSD9ZjzzgR92s/AwS5ARjZ15x6McZwEnAg3gHgqY25m4N
ZvoYpOru2HC2XIupAJ0W9hEGQ44IhbIHecLtMVf6oBXFTrg1vXXKi03LRHiWWDWL
7H8SIG6UaoFvIcpNv0W88EclXzQG6cpIecBm0Zeu8QsHo1Ut87iWo5o/1XNTloY/
BtAFdOC+dbSN1a64UlbQelRcaO5LJzlZTy0cRrH00w9QCUpdxDp2BfxKSyXaWrLP
ewIDAQAB
-----END PUBLIC KEY-----"""

class LicenseService:
    def __init__(self):
        self.public_key = serialization.load_pem_public_key(
            PUBLIC_KEY_PEM.encode()
        )
        # Store license in user home dir
        self.license_path = Path.home() / ".k24" / "license.json"
        self.license_path.parent.mkdir(exist_ok=True)

    def generate_hardware_id(self) -> str:
        """
        Generates a unique hardware fingerprint.
        Combines Node Name, Machine Type, and OS to lock to specific user/hardware.
        """
        try:
            # Platform specific info
            info = [
                platform.node(),
                platform.machine(),
                platform.system(),
                platform.processor()
            ]
            # Join and hash
            raw_id = "|".join(filter(None, info))
            return hashlib.sha256(raw_id.encode()).hexdigest()
        except Exception:
            return "unknown_hardware"

    def validate_license(self) -> dict:
        """
        Reads license file and verifies:
        1. Signature is valid (signed by K24 Server Private Key)
        2. Hardware ID matches this machine
        3. Not expired
        """
        if not self.license_path.exists():
            return {"valid": False, "reason": "No license found"}

        try:
            with open(self.license_path, "r") as f:
                license_data = json.load(f)
            
            payload = license_data.get("payload", {})
            signature_b64 = license_data.get("signature", "")

            # 1. Verify Signature
            if not signature_b64:
                return {"valid": False, "reason": "Missing signature"}
            
            signature = base64.b64decode(signature_b64)
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            
            try:
                self.public_key.verify(
                    signature,
                    payload_bytes,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            except Exception:
                return {"valid": False, "reason": "Invalid signature (Tampered)"}

            # 2. Verify Hardware Binding
            current_hw_id = self.generate_hardware_id()
            if payload.get("hardware_id") != current_hw_id:
                # Allow 'universal' licenses for dev/testing if needed, but strict for prod
                if payload.get("type") != "universal":
                    return {"valid": False, "reason": "License is locked to another device"}

            # 3. Verify Expiry
            expires_at = payload.get("expires_at")
            if expires_at:
                expiry = datetime.fromisoformat(expires_at)
                if datetime.now() > expiry:
                    return {"valid": False, "reason": "License expired"}

            return {
                "valid": True, 
                "plan": payload.get("plan", "pro"),
                "expires_at": expires_at
            }

        except json.JSONDecodeError:
            return {"valid": False, "reason": "Corrupt license file"}
        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}

    def activate_license(self, license_key_content: str) -> dict:
        """
        Saves a provided license key (JSON string) to disk if valid.
        """
        try:
            # Parse input (it might be the full JSON blob)
            data = json.loads(license_key_content)
            
            # Temporary save to validate
            temp_path = self.license_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f)
            
            # Use self to validate
            # Hack: swap path temporarily or just refactor validate to take data
            # Refactoring validate_license to take optional data would be better
            # But let's just use the logic here duplicate for now (or minimal check)
            
            payload = data.get("payload", {})
            signature_b64 = data.get("signature", "")
            
            signature = base64.b64decode(signature_b64)
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            
            self.public_key.verify(
                signature,
                payload_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Check Hardware ID
            if payload.get("hardware_id") != self.generate_hardware_id():
                 if payload.get("type") != "universal":
                     return {"success": False, "error": "This license belongs to a different machine."}

            # Save real file
            with open(self.license_path, "w") as f:
                json.dump(data, f)
                
            return {"success": True}
            
        except json.JSONDecodeError:
             return {"success": False, "error": "Invalid license format"}
        except Exception as e:
             return {"success": False, "error": "Invalid license signature"}

license_service = LicenseService()
