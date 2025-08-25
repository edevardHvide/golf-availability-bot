@echo off
REM Golf Availability Monitor - Streamlit App Startup Script (Windows)
REM This batch file starts both the FastAPI backend and Streamlit frontend

echo 🏌️ Starting Golf Availability Monitor Web Interface...

REM Check if virtual environment exists
if exist "..\venv\Scripts\activate.bat" (
    echo 🐍 Activating virtual environment...
    call ..\venv\Scripts\activate.bat
) else if exist "..\.venv\Scripts\activate.bat" (
    echo 🐍 Activating virtual environment...
    call ..\.venv\Scripts\activate.bat
) else (
    echo ⚠️  Warning: No virtual environment found
    echo Consider running: python -m venv venv
)

REM Install dependencies if needed
if not exist "requirements_installed.flag" (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    echo. > requirements_installed.flag
)

REM Start FastAPI backend in background
echo 🚀 Starting API server...
start "Golf Monitor API" python api_server.py

REM Wait a moment for API to start
timeout /t 3 /nobreak > nul

REM Start Streamlit frontend
echo 🌐 Starting Streamlit app...
start "Golf Monitor UI" streamlit run app.py --server.address 0.0.0.0 --server.port 8501

echo.
echo ✅ Both services are starting!
echo 📱 Streamlit App: http://localhost:8501
echo 🔗 API Documentation: http://localhost:8000/docs
echo.
echo Press any key to exit (Note: Services will continue running in separate windows)
pause
