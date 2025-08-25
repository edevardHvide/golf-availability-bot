# Simple Streamlit App Tester
# Run this from the streamlit_app directory

Write-Host "🏌️ Golf Monitor - Quick Test" -ForegroundColor Green

# Check current directory
if (-not (Test-Path "api_server.py")) {
    Write-Host "❌ Error: Not in streamlit_app directory" -ForegroundColor Red
    Write-Host "Current location: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "Please navigate to the streamlit_app directory first" -ForegroundColor Yellow
    exit 1
}

# Find Python executable
$pythonExe = $null

# Try virtual environment first
$venvPython = "C:\Users\pt1004\git\golf-availability-bot\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    Write-Host "✅ Using virtual environment Python" -ForegroundColor Green
} else {
    # Try system Python
    try {
        $systemPython = (Get-Command python.exe -ErrorAction Stop).Source
        $pythonExe = $systemPython
        Write-Host "✅ Using system Python: $systemPython" -ForegroundColor Green
    } catch {
        Write-Host "❌ Python not found" -ForegroundColor Red
        exit 1
    }
}

# Start API server
Write-Host "🚀 Starting API server..." -ForegroundColor Cyan
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList "api_server.py" -PassThru -WindowStyle Hidden

# Wait a moment
Start-Sleep 3

# Check if API is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "✅ API server is running!" -ForegroundColor Green
    Write-Host "Health check response: $($response.status)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ API server failed to start" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    if ($apiProcess -and !$apiProcess.HasExited) {
        $apiProcess.Kill()
    }
    exit 1
}

# Start Streamlit
Write-Host "🌐 Starting Streamlit app..." -ForegroundColor Cyan
$streamlitExe = "C:\Users\pt1004\git\golf-availability-bot\.venv\Scripts\streamlit.exe"

if (Test-Path $streamlitExe) {
    $streamlitProcess = Start-Process -FilePath $streamlitExe -ArgumentList "run", "app.py", "--server.port", "8501" -PassThru
} else {
    $streamlitProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "streamlit", "run", "app.py", "--server.port", "8501" -PassThru
}

Write-Host ""
Write-Host "✅ Both services started!" -ForegroundColor Green
Write-Host "📱 Streamlit App: http://localhost:8501" -ForegroundColor Cyan
Write-Host "🔗 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop services, or close this window" -ForegroundColor Yellow

# Keep script running and monitor processes
try {
    while ($true) {
        Start-Sleep 5
        
        # Check if processes are still running
        if ($apiProcess.HasExited) {
            Write-Host "⚠️ API server stopped" -ForegroundColor Yellow
            break
        }
        
        if ($streamlitProcess.HasExited) {
            Write-Host "⚠️ Streamlit app stopped" -ForegroundColor Yellow
            break
        }
    }
} catch {
    Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
} finally {
    # Cleanup
    if ($apiProcess -and !$apiProcess.HasExited) {
        $apiProcess.Kill()
        Write-Host "API server stopped" -ForegroundColor Yellow
    }
    if ($streamlitProcess -and !$streamlitProcess.HasExited) {
        $streamlitProcess.Kill()
        Write-Host "Streamlit app stopped" -ForegroundColor Yellow
    }
}
