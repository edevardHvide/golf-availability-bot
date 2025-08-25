#!/usr/bin/env pwsh
# PowerShell script to run golf monitor with cloud API

# Set your Render app URL here
$env:API_URL = "https://your-app-name.onrender.com"

Write-Host "🌐 Using cloud API: $env:API_URL" -ForegroundColor Green
Write-Host "🏌️ Starting Golf Availability Monitor..." -ForegroundColor Cyan

# Run the golf monitor
python golf_availability_monitor.py @args
