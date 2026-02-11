@echo off
echo ===================================================
echo      Starting K24 Intelligent ERP (Complete)
echo ===================================================
echo.

echo 1. Starting Backend Server (API & Tally Integration)...
start "K24 Backend" cmd /k "uvicorn backend.api:app --port 8001 --host 0.0.0.0 --reload"

echo 2. Starting Frontend (Next.js)...
start "K24 Frontend" cmd /k "cd frontend && npm start"

echo 3. Starting Baileys Server (WhatsApp Listener)...
start "K24 WhatsApp Agent" cmd /k "cd baileys-listener && npm start"

echo.
echo ===================================================
echo All Services Launching...
echo - Backend: http://localhost:8001
echo - Frontend: http://localhost:3000
echo - Baileys: Running in background
echo.
echo Note: Tally Agent logic is integrated in the Backend.
echo Keep these windows open.
echo ===================================================
pause
