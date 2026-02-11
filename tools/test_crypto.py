from passlib.context import CryptContext
import bcrypt
import sys

print(f"Bcrypt version: {bcrypt.__version__}")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Test hash generation
try:
    test_hash = pwd_context.hash("password123")
    print(f"Hash generated: {test_hash}")

    # Test verification
    is_valid = pwd_context.verify("password123", test_hash)
    print(f"Verification works: {is_valid}")
except Exception as e:
    print(f"Crypto Test Failed: {e}")
    sys.exit(1)
