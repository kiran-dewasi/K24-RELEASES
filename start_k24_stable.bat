@echo off
echo ===================================================
echo      Starting K24 Services (Stable Mode)
echo ===================================================
echo.
echo NOTE: Switched to Local Database (SQLite) due to connection errors.
echo.

echo 1. Starting Backend (Port 8000)...
echo    (Using Port 8000 as per recent attempts)
start "K24 Backend" cmd /k "uvicorn backend.api:app --port 8000 --host 0.0.0.0 --reload"

echo 2. Starting Baileys Listener (npm start)...
start "K24 Baileys" cmd /k "cd baileys-listener && npm start"

echo 3. Starting Frontend (npm run dev)...
echo    Setting API Port to 8000 explicitly for this session.
set NEXT_PUBLIC_API_URL=http://localhost:8000
start "K24 Frontend" cmd /k "cd frontend && set NEXT_PUBLIC_API_URL=http://localhost:8000 && npm run dev"

echo 4. Starting Tally Agent (Celery Worker)...
start "K24 Tally Agent" cmd /k "celery -A backend.celery_app worker --pool=solo --loglevel=info"

echo.
echo ===================================================
echo Services launching using Local DB.
echo - Backend: http://localhost:8000/docs
echo - Frontend: http://localhost:3000
echo ===================================================
pause
