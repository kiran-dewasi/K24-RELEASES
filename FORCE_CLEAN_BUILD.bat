@echo off
echo [INFO] FORCE KILLING PROCESSES...
taskkill /F /IM k24-backend* 2>nul
taskkill /F /IM k24-listener* 2>nul
taskkill /F /IM app.exe 2>nul
taskkill /F /IM K24.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM python.exe 2>nul

echo.
echo [INFO] CLEANING TEMP FILES...
rmdir /s /q build_temp 2>nul
rmdir /s /q frontend\src-tauri\binaries 2>nul
mkdir frontend\src-tauri\binaries

echo.
echo [INFO] REBUILDING BACKEND (Sidecar)...
venv\Scripts\python scripts\build_sidecars.py
if %errorlevel% neq 0 (
    echo [ERROR] Backend compilation failed.
    exit /b 1
)

echo.
echo [INFO] PREPARING BINARIES (Listener + Backend)...
venv\Scripts\python scripts\prepare_binaries.py

echo.
echo [INFO] BUILDING FRONTEND...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed.
    exit /b 1
)

echo.
echo [INFO] BUILDING INSTALLER...
call npx tauri build

echo.
echo [SUCCESS] NEW CLEAN BUILD READY.
cd ..
explorer "frontend\src-tauri\target\release\bundle\nsis"
