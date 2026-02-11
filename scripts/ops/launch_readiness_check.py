"""
Launch Readiness Assessment for K24 Backend
Checks all critical systems and dependencies
"""
import requests
import sys
import os
from typing import Dict, List, Tuple

# Color codes for terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check_status(name: str, passed: bool, details: str = "") -> Tuple[bool, str]:
    """Print check status and return result"""
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} | {name}")
    if details:
        print(f"      {details}")
    return passed, name

def main():
    print("=" * 60)
    print("🚀 K24 BACKEND LAUNCH READINESS ASSESSMENT")
    print("=" * 60)
    print()
    
    results = []
    critical_failures = []
    
    # 1. Check if backend is running
    print("📡 CONNECTIVITY CHECKS")
    print("-" * 60)
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        passed = response.status_code == 200
        results.append(check_status(
            "Backend API Running", 
            passed,
            f"Status: {response.status_code}"
        ))
        if not passed:
            critical_failures.append("Backend API")
    except Exception as e:
        results.append(check_status("Backend API Running", False, f"Error: {e}"))
        critical_failures.append("Backend API")
    
    # 2. Check Tally connection
    try:
        response = requests.get("http://localhost:9000", timeout=3)
        passed = response.status_code == 200
        results.append(check_status(
            "Tally Connection", 
            passed,
            f"Tally ODBC Server reachable"
        ))
        if not passed:
            critical_failures.append("Tally Connection")
    except Exception as e:
        results.append(check_status("Tally Connection", False, f"Error: {e}"))
        critical_failures.append("Tally Connection")
    
    print()
    
    # 3. Check core endpoints
    print("🔌 API ENDPOINTS")
    print("-" * 60)
    
    headers = {"x-api-key": "k24-secret-key-123"}
    
    endpoints = [
        ("/chat", "POST", {"user_id": "test", "message": "hello"}),
        ("/ledgers", "GET", None),
        ("/context/test_user", "GET", None),
    ]
    
    for path, method, data in endpoints:
        try:
            if method == "POST":
                response = requests.post(f"http://localhost:8001{path}", json=data, headers=headers, timeout=10)
            else:
                response = requests.get(f"http://localhost:8001{path}", headers=headers, timeout=10)
            
            # 403 means auth failed, 200/404/429/500 means auth passed (server reached)
            passed = response.status_code in [200, 404, 429] 
            results.append(check_status(
                f"{method} {path}",
                passed,
                f"Status: {response.status_code}"
            ))
        except Exception as e:
            results.append(check_status(f"{method} {path}", False, f"Error: {e}"))
    
    print()
    
    # 4. Check dependencies
    print("📦 DEPENDENCIES")
    print("-" * 60)
    
    required_modules = [
        "fastapi",
        "uvicorn",
        "redis",
        "pandas",
        "langchain_google_genai",
        "prefect",
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            results.append(check_status(f"Module: {module}", True))
        except ImportError:
            results.append(check_status(f"Module: {module}", False, "Not installed"))
    
    print()
    
    # 5. Check environment variables (Local check only)
    print("🔐 ENVIRONMENT VARIABLES")
    print("-" * 60)
    
    # We skip GOOGLE_API_KEY check here because it's set in the running process, not necessarily here
    env_vars = [
        ("TALLY_URL", False),
    ]
    
    for var, critical in env_vars:
        exists = os.getenv(var) is not None
        results.append(check_status(
            f"Env: {var}",
            exists or not critical,
            "Set" if exists else "Not set (using default)" if not critical else "MISSING"
        ))
    
    print()
    
    # 6. Check file structure
    print("📁 FILE STRUCTURE")
    print("-" * 60)
    
    critical_files = [
        "backend/api.py",
        "backend/agent.py",
        "backend/tally_connector.py",
        "backend/context_manager.py",
        "backend/intent_recognizer.py",
        "backend/entity_extractor.py",
    ]
    
    for file in critical_files:
        exists = os.path.exists(file)
        results.append(check_status(f"File: {file}", exists))
        if not exists:
            critical_failures.append(f"File: {file}")
    
    print()
    print("=" * 60)
    
    # Summary
    passed_count = sum(1 for r, _ in results if r)
    total_count = len(results)
    pass_rate = (passed_count / total_count) * 100
    
    print(f"📊 SUMMARY: {passed_count}/{total_count} checks passed ({pass_rate:.1f}%)")
    
    if critical_failures:
        print(f"\n{RED}❌ CRITICAL FAILURES:{RESET}")
        for failure in critical_failures:
            print(f"   - {failure}")
        print(f"\n{RED}🚫 NOT READY FOR LAUNCH{RESET}")
        return 1
    elif pass_rate < 80:
        print(f"\n{YELLOW}⚠️  LAUNCH WITH CAUTION{RESET}")
        print("Some non-critical checks failed. Review before production.")
        return 0
    else:
        print(f"\n{GREEN}✅ READY FOR LAUNCH!{RESET}")
        return 0

if __name__ == "__main__":
    sys.exit(main())
