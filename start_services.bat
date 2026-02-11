@echo off
echo ===================================================
echo      Starting K24 Services (User Config)
echo ===================================================
echo.

echo 1. Starting Backend (Uvicorn)...
start "K24 Backend" cmd /k "uvicorn backend.api:app --port 8001 --host 0.0.0.0 --reload"

echo 2. Starting Baileys Listener (npm start)...
start "K24 Baileys" cmd /k "cd baileys-listener && npm start"

echo 3. Starting Frontend (npm start)...
echo    Note: This runs the production build. If it fails, run 'npm run dev' instead.
start "K24 Frontend" cmd /k "cd frontend && npm start"

echo 4. Starting Tally Agent (Celery Worker)...
echo    This handles the background Tally tasks.
echo    ("tally_engine.py" is a library, running Celery instead)
start "K24 Tally Agent" cmd /k "celery -A backend.celery_app worker --pool=solo --loglevel=info"

echo.
echo ===================================================
echo Services launching in separate windows.
echo - Backend: http://localhost:8001
echo - Frontend: http://localhost:3000
echo ===================================================
pause
