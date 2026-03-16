#!/usr/bin/env python3
import re
from pathlib import Path

FRONTEND_SRC = Path("frontend/src")
SKIP_FILES = {"api.ts", "api-config.ts"}
report = []

def fix_file(filepath):
    content = filepath.read_text(encoding='utf-8')
    original = content
    changes = 0

    # T1: Replace imports
    if re.search(r'apiClient.*from.*api-config', content):
        content = re.sub(r'import\s*\{\s*(API_CONFIG,\s*)?apiClient\s*\}\s*from\s*["\']@/lib/api-config["\'];?', 'import { api } from "@/lib/api";', content)
        changes += 1

    # T2: Simple GET - apiClient(endpoint) -> api.get(endpoint)
    content = re.sub(r'await\s+apiClient\((["\'][^"\']+["\'])\)(?!\s*,)', r'await api.get(\1)', content)

    # T3: POST/PUT/DELETE - apiClient(endpoint, {method: 'X', body: JSON.stringify(data)}) -> api.x(endpoint, data)
    content = re.sub(r'await\s+apiClient\((["\'][^"\']+["\'])\s*,\s*\{\s*method:\s*["\']POST["\']\s*,\s*body:\s*JSON\.stringify\((\w+)\)\s*\}\s*\)', r'await api.post(\1, \2)', content)
    content = re.sub(r'await\s+apiClient\((["\'][^"\']+["\'])\s*,\s*\{\s*method:\s*["\']PUT["\']\s*,\s*body:\s*JSON\.stringify\((\w+)\)\s*\}\s*\)', r'await api.put(\1, \2)', content)
    content = re.sub(r'await\s+apiClient\((["\'][^"\']+["\'])\s*,\s*\{\s*method:\s*["\']DELETE["\']\s*\}\s*\)', r'await api.delete(\1)', content)

    # T4: Hardcoded localhost (skip api.ts)
    if filepath.name not in SKIP_FILES:
        content = re.sub(r'http://localhost:8001(?!["\'])', r"process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001'", content)
        content = re.sub(r'http://127\.0\.0\.1:8001(?!["\'])', r"process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001'", content)

    # T5: Navbar special case
    if filepath.name == "Navbar.tsx":
        if "checkBackendStatus" not in content:
            content = re.sub(r'import\s*\{([^}]*)\}\s*from\s*["\']@/lib/api["\'];', r'import {\1, checkBackendStatus } from "@/lib/api";', content)
        content = re.sub(r'const\s+res\s*=\s*await\s+fetch\([^)]*health[^)]*\).*?setSyncHealth\(\{[^}]*\}\);',
                         'const status = await checkBackendStatus();\n                if (status.running) { setSyncHealth({ connected: true, lastSync: new Date().toISOString() }); localStorage.setItem("k24_sync_status", JSON.stringify({ connected: true, lastSync: new Date().toISOString() })); } else { setSyncHealth({ connected: false, lastSync: null }); }',
                         content, flags=re.DOTALL)

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return 1
    return 0

total = 0
for fp in FRONTEND_SRC.rglob("*.ts*"):
    if fp.name in SKIP_FILES or fp.suffix not in ['.ts', '.tsx']:
        continue
    if fix_file(fp):
        print(f"OK {fp.relative_to(FRONTEND_SRC.parent)}")
        total += 1

print(f"\n{total} files modified")
Path("fix_api_calls_report.txt").write_text(f"{total} files modified\n")
