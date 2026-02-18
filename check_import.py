import sys
print(f"Python: {sys.version}")

# Test sentry_sdk directly with try/except (same as our fix)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    print("OK: sentry_sdk")
except Exception as e:
    print(f"WARNING: sentry_sdk unavailable: {type(e).__name__}: {e}")
    sentry_sdk = None

# Now test the full backend
try:
    from backend.api import app
    print("SUCCESS: backend.api imported OK")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\nROOT CAUSE: {type(e).__name__}: {e}")
