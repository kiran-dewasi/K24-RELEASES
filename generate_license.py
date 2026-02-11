
import json
import base64
import hashlib
import platform
from datetime import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# SERVER PRIVATE KEY (Simulation) - In real world, this stays on secure server
PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDFZUVgXuOxCL7P
xb7kVlfljlTDQlkuT9if9CQwCAYHuAoNLPyesfoNkQYa7fmCy8fMe63lcjjhiv6a
YTx08aXY8N1VYQmQH5iO9QYNbopIP1mPPOBH3az8DBLkBGNnXnHoxxnAScCDeAeC
pjbmbg1m+hik6u7YcLZci6kAnRb2EQZDjgiFsgd5wu0xV/qgFcVOuDW9dcqLTctE
eJZYNYvsfxIgbpRqgW8hyk2/RbzwRyVfNAbpykh5wGbRl67xCwejVS3zuJajmj/V
c1OWhj8G0AV04L51tI3VrrhSVtB6VFxo7ksnOVlPLRxGsfTTD1AJSl3EOnYF/EpL
Jdpass97AgMBAAECggEAUyvL8wKYQmgSad4ChBgjWdxCN7F1fQ90kVTfiINg8xCm
341UdZM87klsPp2Fk4hES5LTHwmlENctVqPgws9slz9JqudDjb/aWmXAIpmwVyem
FzXJtE4hTGPT89IrhgrjyPZXEc+hd2N0GqbpG+dD6182UgqRD45SMCVCVLlbytp8
2O5HaI/N4IuCf8WKZ/c0yh4oHiJuAgHv7I8wbjxeOhlYLmfJ1LmThtksNgS76Lhl
VF2tJPcpVR1yhFfguyazsXdfTkHSw984DhxNtDjVxTxLUfUGhegZT3l4cXkDms+3
SLZGLAmIdIIcKeyfECTjyGHLuQrLSIso92AK9XqqlQKBgQDrsknyG7e+6dZvcDKF
l4JtqWNE0D8Po0aTDx16OKHuPhpeaPvzVpYteCkuSqqtGFAg0C9rnSaod7ACNL6s
f/q39doE499YaoCw1ySmfJUkRCUINLn8sppYWT4U8amVdbrGm1wrPZBTyyrQZLEp
m/h4kIKSTLxXOkH5Rs6MqNcY/wKBgQDWZlmiazotte0MDL/iYzJlG9PPah1U02tu
5tXoHVzeDuNbgvmkiSPikCt663G/QxKViu8j0yyxA0kCPLu9qA8TNQZNwTBnDMpB
r39ROimG4EwBJYp5XeowTGL+B0AsJQDOQPWpdzuvpOyoHjNZBiFjT3k6aroAj326
FTpOTnIthQKBgBVz09Eqfq3swKzB7IdGRAPRMAzaW3MD7G+EJ62xK+PwWRwQuCXs
0pxu3GivORuqI9joufg0hIk+45E/1b8DowFNajuZtgFpKC9wVZCltDlpzmkRy3/Z
jbzO2pyzZjkJTye2ikwRPWqzCkGPeKSN4q6ukIPaYiYaUljq/e/FilZnAoGAQZlH
S56rSlkjklBEVawsOytsf0Xke5PEh0YxpLd3NqovfkxwvZsIU8Xwx8dKIk8PXJoJ
2Vg/kFmE+R5EAx9snV/X8epuONl8+OQNfHjjQ9VU6/TkjYXipax5jWgChn8749+U
SqmkpXU8w6OZ6l8p0Az89pa5GnrM6SadlGAEJ1ECgYEAnYIWh7X//5PU279SPLRL
cuwjTis959OW38JD8QEOpDbjkQYzg8VCb7fpDmXy2bsuXAhMuKzTd7nA8ILDhIe2
Z+A9AJL8LtA8uBLkPjMdsRPqY46ovy/Gn1aC+qCS+R+yQKlNjQiyxokalblZnVj6
C1J5M15BjdMLn4TgX1xM/LY=
-----END PRIVATE KEY-----"""

def get_hardware_id():
    # Same logic as license_service.py
    try:
        info = [
            platform.node(),
            platform.machine(),
            platform.system(),
            platform.processor()
        ]
        raw_id = "|".join(filter(None, info))
        return hashlib.sha256(raw_id.encode()).hexdigest()
    except Exception:
        return "unknown"

def generate_license():
    print("=== K24 License Generator (Admin Tool) ===")
    
    # 1. Hardware ID
    hw_id = get_hardware_id()
    print(f"Detected Hardware ID: {hw_id}")
    print("Press Enter to use this ID, or paste another machine's ID:")
    custom_id = input("> ").strip()
    if custom_id:
        hw_id = custom_id
        
    # 2. Plan
    plan = "pro"
    
    # 3. Expiry
    days = 365
    expires_at = datetime.now()  # Not used for delta here, just current time base
    # Calculate expiry date string
    # Assuming user wants 1 year from now
    from datetime import timedelta
    expiry_date = (datetime.now() + timedelta(days=365)).isoformat()
    
    payload = {
        "hardware_id": hw_id,
        "plan": plan,
        "expires_at": expiry_date,
        "type": "standard", # 'universal' = works everywhere
        "issued_at": datetime.now().isoformat()
    }
    
    # 4. Sign
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PEM.encode(),
        password=None
    )
    
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = private_key.sign(
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    license_data = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode()
    }
    
    license_json = json.dumps(license_data, indent=2)
    print("\nGenerated License:")
    print(license_json)
    
    # Option to save
    print("\nSave to local license file? (y/n)")
    if input("> ").lower().startswith('y'):
        import pathlib
        path = pathlib.Path.home() / ".k24" / "license.json"
        path.parent.mkdir(exist_ok=True)
        with open(path, "w") as f:
            f.write(license_json)
        print(f"Saved to {path}")

if __name__ == "__main__":
    generate_license()
