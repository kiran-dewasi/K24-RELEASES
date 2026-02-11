@echo off
echo ==========================================
echo       K24 SELF-REPAIR & BUILD TOOL
echo ==========================================
echo.
echo [INFO] Diagnosis:
echo 1. The app "kills itself" because the backend sidecar crashes on startup due to a legacy emojii issue in "api.py" on Windows.
echo 2. The "old UI" persists because the build failure prevented the new installer from being created.
echo.
echo [ACTION] Starting repair process...
echo.

REM --- STEP 1: CLEAN UP OLD ARTIFACTS ---
echo [STEP 1] Cleaning up old binaries...
if exist "backend\dist" rmdir /s /q "backend\dist"
if exist "frontend\src-tauri\binaries\k24-backend-x86_64-pc-windows-msvc.exe" (
    echo [INFO] Removing old backend binary...
    del "frontend\src-tauri\binaries\k24-backend-x86_64-pc-windows-msvc.exe"
)

REM --- STEP 2: REBUILD BACKEND SIDECAR ---
echo.
echo [STEP 2] Compiling Backend Sidecar (This is the critical fix)...
echo [WAIT] This process uses PyInstaller and takes 5-10 minutes. Please be patient.
call venv\Scripts\python scripts/build_sidecars.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backend build failed!
    echo [Check] Ensure Python venv is valid and "pyinstaller" is installed.
    pause
    exit /b 1
)
echo [SUCCESS] Backend binary compiled successfully!

REM --- STEP 3: LISTENER SIDECAR ---
echo.
echo [STEP 3] Checking for WhatsApp Listener...
if not exist "frontend\src-tauri\binaries\k24-listener-x86_64-pc-windows-msvc.exe" (
    echo [INFO] Copying listener binary (if available)...
    call venv\Scripts\python scripts/prepare_binaries.py
)

REM --- STEP 4: BUILD FRONTEND & INSTALLER ---
echo.
echo [STEP 4] Building Frontend and Installer...
cd frontend
echo [INFO] Installing dependencies (if needed)...
if not exist "node_modules" call npm install

echo [INFO] Building Next.js Frontend...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed!
    cd ..
    pause
    exit /b 1
)

echo [INFO] Packaging Tauri App...
call npx tauri build
if %errorlevel% neq 0 (
    echo [ERROR] Tauri build failed!
    cd ..
    pause
    exit /b 1
)
cd ..

REM --- DONE ---
echo.
echo ==========================================
echo [SUCCESS] NEW INSTALLER READY!
echo ==========================================
echo.
echo The new installer (v1.0.1) has been created.
echo Please uninstall the old version and install this new one.
echo.
echo Opening output folder...
explorer "frontend\src-tauri\target\release\bundle\nsis"
pause
