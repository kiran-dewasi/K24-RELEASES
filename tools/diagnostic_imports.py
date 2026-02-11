import sys
import traceback
import os

def test_import(module_name, description=""):
    """Test import and report detailed error"""
    print(f"\n{'='*60}")
    print(f"Testing: {module_name}")
    if description:
        print(f"Purpose: {description}")
    print('='*60)
    
    try:
        mod = __import__(module_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f"[OK] SUCCESS - Version: {version}")
        return True
    except Exception as e:
        print(f"[X] FAILED")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\nFull Traceback:")
        traceback.print_exc()
        return False

# Test in order of dependency
print("=" * 60)
print("K24 BACKEND IMPORT DIAGNOSTIC")
print("=" * 60)

results = {}

# Layer 1: Core Python packages
results['fastapi'] = test_import('fastapi', 'Web framework')
results['uvicorn'] = test_import('uvicorn', 'ASGI server')
results['pydantic'] = test_import('pydantic', 'Data validation')

# Layer 2: Database & Auth
results['sqlite3'] = test_import('sqlite3', 'Local database')
results['passlib'] = test_import('passlib', 'Password hashing')
results['bcrypt'] = test_import('bcrypt', 'Password crypto')
results['jose'] = test_import('jose', 'JWT tokens')

# Layer 3: LangChain (CRITICAL - suspected issue)
results['langchain'] = test_import('langchain', 'AI framework')
results['langchain_core'] = test_import('langchain_core', 'LangChain core')
results['langchain_google_genai'] = test_import('langchain_google_genai', 'Gemini integration')
# results['langgraph'] = test_import('langgraph', 'Agent orchestration') # Skipping detailed check here, focusing on core imports first

# Layer 4: Test Pydantic v1 compatibility
print("\n" + "="*60)
print("PYDANTIC V1 COMPATIBILITY CHECK (Critical for LangChain)")
print("="*60)
try:
    import pydantic
    print(f"Pydantic version: {pydantic.__version__}")
    
    # Check if v1 compat layer exists
    from pydantic.v1 import BaseModel as BaseModelV1
    print("[OK] Pydantic v1 compatibility layer EXISTS")
    
    # Test if LangChain can use it
    # Note: langchain_core.pydantic_v1 might handle imports differently depending on pydantic version
    try:
        from langchain_core.pydantic_v1 import BaseModel
        print("[OK] LangChain can import pydantic_v1")
    except ImportError:
         print("[X] LangChain FAILED to import pydantic_v1")

except ImportError as e:
    print(f"[X] Pydantic v1 compatibility MISSING")
    print(f"Error: {e}")
    print("\n[!] THIS IS LIKELY THE BLOCKER")

# Layer 5: Optional services
# results['supabase'] = test_import('supabase', 'Cloud database (optional)')

# Summary
print("\n" + "="*60)
print("IMPORT TEST SUMMARY")
print("="*60)
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"Passed: {passed}/{total}")

failed = [k for k, v in results.items() if not v]
if failed:
    print(f"\n[X] FAILED IMPORTS: {', '.join(failed)}")
    print("\n[!] CRITICAL: Cannot proceed until these are resolved")
else:
    print("\n[OK] All core imports successful - issue is in application code")
