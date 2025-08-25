# Golf Availability Monitor - Local Test Setup (PowerShell)
# Run this with: .\test_local.ps1

Write-Host "🏌️ Golf Availability Monitor - Local Test Setup" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "app.py")) {
    Write-Host "❌ Error: app.py not found. Make sure you're in the streamlit_app directory." -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python availability
try {
    $pythonVersion = python --version 2>$null
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please ensure Python is installed and in your PATH." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "📦 Installing dependencies with uv..." -ForegroundColor Cyan
try {
    # Check if uv is available
    try {
        $uvVersion = uv --version 2>$null
        Write-Host "✅ uv found: $uvVersion" -ForegroundColor Green
    } catch {
        Write-Host "❌ uv not found. Installing uv first..." -ForegroundColor Yellow
        python -m pip install uv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install uv"
        }
    }
    
    # Install dependencies with uv
    uv pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "uv pip install failed"
    }
    Write-Host "✅ Dependencies installed successfully with uv!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install dependencies: $_" -ForegroundColor Red
    Write-Host "Falling back to regular pip..." -ForegroundColor Yellow
    try {
        python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Pip install also failed"
        }
        Write-Host "✅ Dependencies installed with pip!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Both uv and pip failed: $_" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "🚀 Starting local development server..." -ForegroundColor Cyan
Write-Host ""

# Start the Python runner
try {
    python run_local.py
} catch {
    Write-Host ""
    Write-Host "❌ Server stopped unexpectedly: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
