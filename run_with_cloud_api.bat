@echo off
REM Set your Render app URL here
set API_URL=https://your-app-name.onrender.com

REM Run the golf monitor
python golf_availability_monitor.py %*
