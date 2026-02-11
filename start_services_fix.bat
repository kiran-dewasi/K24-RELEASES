@echo off
echo ===================================================
echo      Starting K24 Services (Fixing Frontend)
echo ===================================================
echo.

echo 1. Starting Backend (Uvicorn)...
start "K24 Backend" cmd /k "uvicorn backend.api:app --port 8001 --host 0.0.0.0 --reload"

echo 2. Starting Baileys Listener (npm start)...
start "K24 Baileys" cmd /k "cd baileys-listener && npm start"

echo 3. Starting Frontend (npm run dev)...
echo    Switching to DEV mode to ensure it starts correctly.
echo    Wait for 'Ready in Xms' message before opening browser.
start "K24 Frontend" cmd /k "cd frontend && npm run dev"

echo 4. Starting Tally Agent (Celery Worker)...
start "K24 Tally Agent" cmd /k "celery -A backend.celery_app worker --pool=solo --loglevel=info"

echo.
echo ===================================================
echo Services launching.
echo PLEASE WAIT 15-30 SECONDS for Frontend to compile.
echo - Backend: http://localhost:8001/docs
echo - Frontend: http://localhost:3000
echo ===================================================
pause
