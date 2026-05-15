@echo off
echo ========================================
echo  NSE AI Stock Analyst - Starting System
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
)

REM Check if .env exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please create a .env file with your OPENROUTER_API_KEY
    echo Example:
    echo OPENROUTER_API_KEY=sk-or-v1-your-key-here
    echo.
    pause
)

REM Start the server
echo.
echo ========================================
echo  Starting FastAPI Server + Frontend
echo  Access dashboard at: http://localhost:8000
echo ========================================
echo.

python main.py

pause
