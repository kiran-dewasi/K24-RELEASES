# Start the backend server with correct PYTHONPATH so 'from backend.xxx import ...' works inside subprocesses
$env:PYTHONPATH = $PSScriptRoot
uvicorn backend.api:app --port 8001 --host 127.0.0.1 --reload
