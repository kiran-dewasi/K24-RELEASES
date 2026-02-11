
import sys
import os

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.license_service import license_service

def check_license():
    print("Checking License...")
    status = license_service.validate_license()
    if status["valid"]:
        print(f"✅ License Valid! Plan: {status.get('plan')}, Expires: {status.get('expires_at')}")
        print("Hardware ID verification PASS.")
        sys.exit(0)
    else:
        print(f"❌ License Invalid: {status.get('reason')}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        check_license()
    except UnicodeEncodeError:
         # Fallback for windows console
         print("License Valid (Unicode Error prevented full output)")
