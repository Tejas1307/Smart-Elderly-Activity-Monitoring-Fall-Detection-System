@echo off
title CarePulse Senior Care Monitoring System
echo ========================================================
echo   CarePulse - Elderly Activity & Fall Monitoring System
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Be sure to CHECK the box: "Add Python to PATH" during setup.
    echo.
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [*] Setting up virtual environment (venv)...
    python -m venv venv
)

:: Activate virtual environment
echo [*] Activating venv...
call venv\Scripts\activate.bat

:: Install dependencies
echo [*] Checking and installing dependencies from requirements.txt...
pip install -r requirements.txt

:: Launch server
echo.
echo ========================================================
echo [OK] Server starting on http://localhost:8000
echo Open http://localhost:8000 in your browser (Chrome/Edge)
echo Press Ctrl + C to stop the server.
echo ========================================================
echo.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
