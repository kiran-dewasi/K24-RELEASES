@echo off
echo [INFO] Preparing K24 Desktop Build...

REM 1. Check for Rust
cargo --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Rust is not installed. Please install from https://rustup.rs/
    echo [INFO] After installing, restart your terminal and run this script again.
    pause
    exit /b 1
)

REM 2. Prepare Sidecars (Backend & Listener)
echo [INFO] Organizing Sidecar Binaries...
call venv\Scripts\python scripts\prepare_binaries.py

REM 3. Disable Next.js Middleware (Incompatible with Static Export)
if exist "frontend\src\middleware.ts" (
    echo [INFO] Disabling Middleware for Static Export...
    ren "frontend\src\middleware.ts" "middleware.ts.disabled"
)

REM 4. Run Tauri Build
echo [INFO] Check for dependencies...
cd frontend
if not exist "node_modules" call npm install
echo [INFO] Building K24 Desktop App (This may take 10+ minutes)...
call npx tauri build
cd ..

REM 5. Restore Middleware
if exist "frontend\src\middleware.ts.disabled" (
    echo [INFO] Restoring Middleware...
    ren "frontend\src\middleware.ts.disabled" "middleware.ts"
)

echo [DONE] content should be in frontend/src-tauri/target/release
pause
