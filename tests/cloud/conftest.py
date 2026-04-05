import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
cloud_backend_root = os.path.join(repo_root, 'cloud-backend')

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Cloud backend root — resolves `database` to cloud-backend/database/
if cloud_backend_root not in sys.path:
    sys.path.insert(0, cloud_backend_root)
