@echo off
echo ===================================
echo ShadowHunter Agent Monitor
echo Full Visibility Mode
echo ===================================
echo.
cd /d "C:\shadowhunter"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

echo Starting agent monitor...
echo This will report ALL wallet activity to Telegram
echo.
echo Press Ctrl+C to stop
echo.

python agent_full_visibility.py

if errorlevel 1 (
    echo.
    echo Agent stopped with error
    pause
) else (
    echo.
    echo Agent stopped
    pause
)
