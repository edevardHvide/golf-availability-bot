@echo off
echo 🏌️ Golf Availability Monitor - Local Test Setup
echo ============================================

REM Check if we're in the right directory
if not exist "app.py" (
    echo ❌ Error: app.py not found. Make sure you're in the streamlit_app directory.
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo 📦 Installing dependencies with uv...
uv pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo ❌ uv failed, falling back to pip...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo 🚀 Starting local development server...
echo.

REM Start the Python runner
python run_local.py

REM If we get here, something went wrong
echo.
echo ❌ Server stopped unexpectedly
pause
