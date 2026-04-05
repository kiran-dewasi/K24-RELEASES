import os
import shutil
from pathlib import Path

base_dir = Path(r"c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare")

removed_size = 0
removed_count = 0

def get_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total

def safe_remove(p):
    global removed_size, removed_count
    if p.exists() and p.is_dir():
        try:
            size = get_size(p)
            shutil.rmtree(p, ignore_errors=True)
            removed_size += size
            removed_count += 1
            print(f"Deleted: {p.relative_to(base_dir)}")
        except Exception as e:
            print(f"Failed to delete {p.relative_to(base_dir)}: {e}")

# Exact targets to remove
explicit_targets = [
    base_dir / "frontend" / ".next",
    base_dir / "frontend" / "build",
    base_dir / "build",
]

for t in explicit_targets:
    safe_remove(t)

# Walk for __pycache__ and others
for root, dirs, files in os.walk(base_dir):
    if 'node_modules' in dirs:
        dirs.remove('node_modules')
    if '.git' in dirs:
        dirs.remove('.git')
        
    for d in list(dirs):
        if d in ("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"):
            p = Path(root) / d
            safe_remove(p)
            dirs.remove(d)

print(f"\nCleanup Complete.")
print(f"Total Folders Removed: {removed_count}")
print(f"Approximate Space Saved: {removed_size / (1024*1024):.2f} MB")
