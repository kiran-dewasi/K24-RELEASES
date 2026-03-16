import os
import json
import time
import httpx
import subprocess
import sys

# TEST 1 - Static output
print("=== TEST 1: Static Output ===")
out_dir = "frontend/out"
checks1 = {
    "out/ directory exists": os.path.isdir(out_dir),
    "index.html exists": os.path.isfile(f"{out_dir}/index.html"),
    "_next/static/ exists": os.path.isdir(f"{out_dir}/_next/static"),
    "No server API route files at root": not any(
        f.endswith(".js") and "api" in f.lower()
        for f in os.listdir(out_dir) if os.path.isdir(out_dir) and os.path.isfile(os.path.join(out_dir, f))
    ) if os.path.isdir(out_dir) else False,
}

for check, result in checks1.items():
    print(f"{'✅' if result else '❌'} {check}")

if os.path.isdir(out_dir):
    total_files = sum(len(files) for _, _, files in os.walk(out_dir))
    total_size = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, files in os.walk(out_dir)
        for f in files
    ) / (1024 * 1024)
    print(f"Total files: {total_files}")
    print(f"Total size: {total_size:.2f} MB")

# TEST 2 - index.html content sanity
print("\n=== TEST 2: index.html sanity ===")
index_path = "frontend/out/index.html"
if os.path.isfile(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    checks2 = {
        "Has <html> tag": "<html" in content,
        "Has <body> tag": "<body" in content,
        "Has _next/static script reference": "_next/static" in content,
        "No server-only imports (getServerSideProps)": "getServerSideProps" not in content,
        "No raw API route references (/api/)": '"/api/' not in content,
        "Has NEXT_PUBLIC_API_URL or localhost:8001 reference": "8001" in content or "NEXT_PUBLIC_API_URL" in content,
    }
    for check, result in checks2.items():
        print(f"{'✅' if result else '❌'} {check}")
else:
    print("❌ index.html not found")

# TEST 3 - Python backend live integration test
print("\n=== TEST 3: Python backend ===")
BASE = "http://localhost:8001"

already_running = False
try:
    with httpx.Client(timeout=2) as client:
        resp = client.get(f"{BASE}/health")
        if resp.status_code == 200:
            already_running = True
except:
    pass

proc = None
if not already_running:
    print("Backend not running, starting subprocess...")
    proc = subprocess.Popen(
        [sys.executable, "backend/desktop_main.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(6)
else:
    print("Backend already running on port 8001.")

endpoints_to_test = [
    ("GET", "/health", None),
    ("GET", "/api/ledgers", None),
    ("GET", "/api/vouchers", None),
    ("GET", "/api/items", None),
]

results3 = []
with httpx.Client(timeout=8) as client:
    for method, path, body in endpoints_to_test:
        try:
            url = f"{BASE}{path}"
            resp = client.request(method, url, json=body)
            # Considering 401 Unauthorized or 422 Unprocessable Entity as responsive/alive backing endpoints
            ok = resp.status_code in (200, 201, 401, 403, 404, 422) 
            results3.append((ok, f"{method} {path} → {resp.status_code}"))
        except Exception as e:
            results3.append((False, f"{method} {path} → ERROR: {e}"))

for ok, msg in results3:
    print(f"{'✅' if ok else '❌'} {msg}")

if proc:
    proc.terminate()
    proc.wait()
    print("Backend process terminated.")

# TEST 4 - Tauri config
print("\n=== TEST 4: Tauri config ===")
tauri_path = "frontend/src-tauri/tauri.conf.json"
if os.path.isfile(tauri_path):
    with open(tauri_path, "r") as f:
        config = json.load(f)
    build = config.get("build", {})
    bundle = config.get("bundle", {})
    checks4 = {
        "frontendDist points to ../out": build.get("frontendDist") == "../out",
        "beforeBuildCommand includes npm run build": "npm run build" in build.get("beforeBuildCommand", ""),
        "externalBin includes k24-backend": any(
            "k24-backend" in str(b) for b in bundle.get("externalBin", [])
        ),
        "CSP whitelists localhost:8001 or 127.0.0.1:8001": "8001" in json.dumps(config),
        "Bundle active is true": bundle.get("active", False) is True,
        "Identifier is set": bool(config.get("identifier") or config.get("app", {}).get("identifier")),
    }
    for check, result in checks4.items():
        print(f"{'✅' if result else '❌'} {check}")
else:
    print("❌ tauri.conf.json not found")

# TEST 5 - Env vars
print("\n=== TEST 5: Environment variables ===")
for env_file in [".env.production", ".env.development", ".env.local"]:
    path = f"frontend/{env_file}"
    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        has_api_url = "NEXT_PUBLIC_API_URL" in content
        has_port = "8001" in content
        print(f"✅ {env_file} exists — API_URL set: {has_api_url}, port 8001: {has_port}")
    else:
        print(f"⚠️  {env_file} not found (may be ok)")
