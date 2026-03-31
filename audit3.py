import os

def search_text(root_dir, search_terms):
    print("Searching for hardcoded tenant/strings...")
    for dirpath, _, filenames in os.walk(root_dir):
        if '.git' in dirpath or 'node_modules' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath:
            continue
        for filename in filenames:
            # only text files
            if not filename.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.html', '.md', '.json', '.txt')):
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        line_lower = line.lower()
                        for term in search_terms:
                            if term in line_lower:
                                print(f"File: {filepath}")
                                print(f"Line: {i+1}")
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                for j in range(start, end):
                                    prefix = ">> " if j == i else "   "
                                    print(f"{prefix}{j+1}: {lines[j].rstrip()}")
                                print("-" * 40)
            except Exception:
                pass

search_text('.', ['tenant-12345', 'tenant_id = "tenant-', "tenant_id = 'tenant-", 'tenant_id="tenant-', "tenant_id='tenant-"])
