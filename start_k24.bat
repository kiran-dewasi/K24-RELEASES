@echo off
echo ==========================================
echo      Starting K24 Intelligent ERP
echo ==========================================
echo.

echo Starting Backend Server (Port 8001)...
start "K24 Backend" /min cmd /c "uvicorn backend.api:app --port 8001 --host 0.0.0.0"

echo Starting Frontend Server (Port 3000)...
cd frontend
start "K24 Frontend" /min cmd /c "npm start"
cd ..

echo.
echo Waiting for services to start...
timeout /t 5 /nobreak >nul

echo Opening K24 in your browser...
start http://localhost:3000

echo.
echo K24 is running! 
echo Keep this window open or minimize it.
echo Close this window to stop K24.
pause
