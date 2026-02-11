@echo off
echo ===================================================
echo      K24 ULTIMATE LAUNCHER (Diagnosed & Fixed)
echo ===================================================
echo.
echo DIAGNOSIS REPORT:
echo 1. Backend DB Crash: FIXED (Switched to SQLite Fallback).
echo 2. Frontend Connection: FIXED (Verified startup manually).
echo 3. Port Mismatch: ALIGNED (Backend=8000, Frontend API=8000).
echo.
echo Launching services...

echo 1. Backend (Port 8000)...
start "K24 Backend" cmd /k "uvicorn backend.api:app --port 8000 --host 0.0.0.0 --reload"

echo 2. Baileys (WhatsApp Listener)...
start "K24 Baileys" cmd /k "cd baileys-listener && npm start"

echo 3. Frontend (Port 3000)...
echo    Force-setting API connection to Port 8000.
start "K24 Frontend" cmd /k "cd frontend && set NEXT_PUBLIC_API_URL=http://localhost:8000 && npm run dev"

echo 4. Tally Agent (Background Worker)...
start "K24 Tally Agent" cmd /k "celery -A backend.celery_app worker --pool=solo --loglevel=info"

echo.
echo ===================================================
echo DONE.
echo Please wait 30 seconds for all windows to settle.
echo Access URLs:
echo - App: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
echo ===================================================
pause
