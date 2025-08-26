@echo off
REM Golf Availability Monitor - Windows Task Scheduler Runner
REM This batch file runs the golf availability monitor with proper environment setup

REM Set the working directory to the script location
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No virtual environment found, using system Python
)

REM Run the golf monitor with default settings
echo Starting Golf Availability Monitor...
python golf_availability_monitor.py --time-window 16:00-18:00 --interval 300 --players 3 --days 3

REM If there's an error, pause to see it (only when run manually)
if errorlevel 1 (
    echo.
    echo Error occurred. Check the output above.
    if "%1" neq "scheduled" pause
)
