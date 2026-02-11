@echo off
echo ===================================================
echo      Starting K24 Intelligent ERP (Development Mode)
echo ===================================================
echo.

echo 1. Starting Backend Server (API & Tally Integration)...
echo    Logs will appear in the backend window.
start "K24 Backend" cmd /k "uvicorn backend.api:app --port 8001 --host 0.0.0.0 --reload"

echo 2. Starting Frontend (Next.js Dev Mode)...
echo    This may take a moment to compile.
start "K24 Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo 3. Starting Baileys Server (WhatsApp Listener)...
start "K24 WhatsApp Agent" cmd /k "cd baileys-listener && npm install && npm start"

echo.
echo ===================================================
echo All Services Launching...
echo - Backend: http://localhost:8001/docs (Check this first)
echo - Frontend: http://localhost:3000
echo.
echo If windows close immediately, there is an error.
echo Check the command prompts for Red Error Messages.
echo ===================================================
pause
