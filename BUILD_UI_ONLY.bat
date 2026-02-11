@echo off
echo ==========================================
echo       K24 UI UPDATE BUILDER (v1.0.2)
echo ==========================================
echo.
echo [INFO] Skipping backend rebuild (already fixed).
echo [INFO] Building only the new Premium UI...
echo.

cd frontend

echo [STEP 1] Building Next.js Frontend...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)

echo.
echo [STEP 2] Packaging Tauri Installer...
call npx tauri build
if %errorlevel% neq 0 (
    echo [ERROR] Tauri build failed!
    pause
    exit /b 1
)

cd ..
echo.
echo [SUCCESS] NEW PREMIUM INSTALLER READY (v1.0.2)!
echo Opening output folder...
explorer "frontend\src-tauri\target\release\bundle\nsis"
pause
