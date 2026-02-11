
import sys
import os
import traceback

# Add backend to path
sys.path.insert(0, os.path.abspath('.'))

print("="*60)
print("BACKEND.API IMPORT TEST (Main Application)")
print("="*60)

try:
    print("\n1. Attempting to import backend.api...")
    from backend.api import app
    
    print("[OK] SUCCESS: backend.api imported")
    print(f"   App object: {app}")
    print(f"   App title: {app.title if hasattr(app, 'title') else 'N/A'}")
    
    # Try to get routes
    print("\n2. Registered routes:")
    for route in app.routes:
        print(f"   - {route.path}")
    
    print("\n[OK] BACKEND IS HEALTHY - Issue might be in startup/config")
    
except Exception as e:
    print(f"\n[X] BACKEND IMPORT FAILED")
    print(f"\nError Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    
    print("\n" + "="*60)
    print("DETAILED STACK TRACE (Find the exact failing line)")
    print("="*60)
    traceback.print_exc()
    
    # Try to extract the failing module
    tb = traceback.extract_tb(e.__traceback__)
    print("\n" + "="*60)
    print("CALL STACK (Most recent call last):")
    print("="*60)
    for frame in tb:
        print(f"File: {frame.filename}")
        print(f"Line: {frame.lineno}")
        print(f"Function: {frame.name}")
        print(f"Code: {frame.line}")
        print("-" * 40)
    
    print("\n[!] THE ISSUE IS IN THE FILE LISTED ABOVE")
