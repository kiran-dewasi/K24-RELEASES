@echo off
echo ==========================================
echo      K24 - Installation Script
echo ==========================================
echo.

echo [1/3] Installing Python Dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing Python dependencies!
    pause
    exit /b
)

echo.
echo [2/3] Installing Frontend Dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo Error installing Frontend dependencies!
    pause
    exit /b
)

echo.
echo [3/3] Building Frontend...
call npm run build
if %errorlevel% neq 0 (
    echo Error building Frontend!
    pause
    exit /b
)
cd ..

echo.
echo ==========================================
echo      Installation Complete! 🚀
echo      Run 'start_k24.bat' to launch.
echo ==========================================
pause
