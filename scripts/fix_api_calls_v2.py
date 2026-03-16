import re
import os
from pathlib import Path

def fix_api_calls(content):
    # POST with body: apiClient('/path', { method: 'POST', body: JSON.stringify(X) }) → api.post('/path', X)
    content = re.sub(
        r"apiClient\(([^,]+),\s*\{\s*method:\s*['\"]POST['\"]\s*,\s*body:\s*JSON\.stringify\(([^)]+)\)\s*\}\s*\)",
        r"api.post(\1, \2)",
        content
    )

    # PUT with body: apiClient('/path', { method: 'PUT', body: JSON.stringify(X) }) → api.put('/path', X)
    content = re.sub(
        r"apiClient\(([^,]+),\s*\{\s*method:\s*['\"]PUT['\"]\s*,\s*body:\s*JSON\.stringify\(([^)]+)\)\s*\}\s*\)",
        r"api.put(\1, \2)",
        content
    )

    # DELETE: apiClient('/path', { method: 'DELETE' }) → api.delete('/path')
    content = re.sub(
        r"apiClient\(([^,]+),\s*\{\s*method:\s*['\"]DELETE['\"]\s*\}\s*\)",
        r"api.delete(\1)",
        content
    )

    return content

def main():
    modified = 0
    frontend_src = Path("frontend/src")

    for filepath in frontend_src.rglob("*.ts*"):
        if "api.ts" in filepath.name or "api-config.ts" in filepath.name:
            continue

        content = filepath.read_text(encoding="utf-8")
        new_content = fix_api_calls(content)

        if new_content != content:
            filepath.write_text(new_content, encoding="utf-8")
            modified += 1

    print(f"Modified {modified} files")

if __name__ == "__main__":
    main()
