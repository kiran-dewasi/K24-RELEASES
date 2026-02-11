@echo off
echo [INFO] STARTING FINAL REPAIR
echo [INFO] 1. Recompiling Backend (Fixes the "Game"/Crash)...
call venv\Scripts\python scripts\build_sidecars.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo [INFO] 2. Building Frontend (Applies Premium UI)...
cd frontend
call npm run build
if %errorlevel% neq 0 exit /b %errorlevel%

echo [INFO] 3. Packaging Installer...
call npx tauri build
cd ..

echo [SUCCESS] DONE!
explorer "frontend\src-tauri\target\release\bundle\nsis"
pause
