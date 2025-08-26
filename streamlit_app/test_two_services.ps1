# PowerShell script to test two-service architecture locally

Write-Host "🚀 Starting Two-Service Architecture Test" -ForegroundColor Green
Write-Host "=" * 50

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Blue
} catch {
    Write-Host "❌ Python not found. Please install Python." -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "`n📦 Checking dependencies..."
$packages = @("fastapi", "uvicorn", "streamlit", "requests")
$missing = @()

foreach ($package in $packages) {
    try {
        python -c "import $package" 2>$null
        Write-Host "✅ $package" -ForegroundColor Green
    } catch {
        Write-Host "❌ $package" -ForegroundColor Red
        $missing += $package
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`n📥 Installing missing packages..." -ForegroundColor Yellow
    foreach ($package in $missing) {
        Write-Host "Installing $package..."
        pip install $package
    }
}

# Function to start API service
function Start-APIService {
    Write-Host "`n🔧 Starting API Service..." -ForegroundColor Blue
    Write-Host "URL: http://localhost:8000"
    Write-Host "Press Ctrl+C to stop"
    Write-Host "-" * 30
    
    try {
        python streamlit_app/render_api_server.py
    } catch {
        Write-Host "❌ Failed to start API service" -ForegroundColor Red
        Write-Host "Make sure you're in the correct directory and all dependencies are installed."
    }
}

# Function to start UI service
function Start-UIService {
    Write-Host "`n🎨 Starting UI Service..." -ForegroundColor Blue
    Write-Host "URL: http://localhost:8501"
    Write-Host "Press Ctrl+C to stop"
    Write-Host "-" * 30
    
    $env:API_BASE_URL = "http://localhost:8000"
    
    try {
        streamlit run streamlit_app/render_streamlit_app.py
    } catch {
        Write-Host "❌ Failed to start UI service" -ForegroundColor Red
        Write-Host "Make sure Streamlit is installed and all dependencies are available."
    }
}

# Function to test services
function Test-Services {
    Write-Host "`n🧪 Testing Services..." -ForegroundColor Blue
    
    try {
        python streamlit_app/test_two_services.py
    } catch {
        Write-Host "❌ Test script failed" -ForegroundColor Red
    }
}

# Main menu
Write-Host "`n🎯 Choose an option:"
Write-Host "1. Start API Service (Port 8000)"
Write-Host "2. Start UI Service (Port 8501)" 
Write-Host "3. Test Services (API must be running)"
Write-Host "4. Exit"

do {
    $choice = Read-Host "`nEnter choice (1-4)"
    
    switch ($choice) {
        "1" { Start-APIService; break }
        "2" { Start-UIService; break }
        "3" { Test-Services; break }
        "4" { 
            Write-Host "👋 Goodbye!" -ForegroundColor Green
            exit 0
        }
        default { 
            Write-Host "❌ Invalid choice. Please enter 1-4." -ForegroundColor Red
        }
    }
} while ($true)
