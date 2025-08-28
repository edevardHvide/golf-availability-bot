@echo off
echo 🏌️ Golf Availability Monitor - No Database Mode
echo ================================================
echo.
echo This will run the golf monitor without attempting to connect to PostgreSQL.
echo Results will be saved to JSON files instead.
echo.
echo Press any key to continue...
pause >nul

echo.
echo Setting DATABASE_ENABLED=false...
set DATABASE_ENABLED=false

echo.
echo Starting golf monitor...
python golf_availability_monitor.py --local --immediate

echo.
echo Monitor finished. Press any key to exit...
pause >nul
