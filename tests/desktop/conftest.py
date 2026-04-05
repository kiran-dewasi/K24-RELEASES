import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
backend_root = os.path.join(repo_root, 'backend')

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Desktop backend root — resolves `database` to backend/database/
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
