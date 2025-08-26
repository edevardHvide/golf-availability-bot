# Enhanced PowerShell startup script for Golf Availability Monitor
# Windows version of the enhanced startup script

Write-Host "🚀 Starting Golf Availability Monitor v2.0 (Windows)" -ForegroundColor Green
Write-Host "=============================================="

# Display environment info
Write-Host "🔧 Environment Information:" -ForegroundColor Cyan
Write-Host "  Python: $(python --version)"
Write-Host "  Working Directory: $(Get-Location)"

# Change to the streamlit_app directory
Set-Location streamlit_app

Write-Host ""
Write-Host "📦 Checking components..." -ForegroundColor Cyan

# Check if robust JSON manager exists
if (Test-Path "robust_json_manager.py") {
    Write-Host "  ✅ Robust JSON Manager available" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Robust JSON Manager not found - using basic JSON" -ForegroundColor Yellow
}

# Check if enhanced unified server exists
$SERVER_FILE = ""
if (Test-Path "enhanced_unified_server.py") {
    Write-Host "  ✅ Enhanced Unified Server available" -ForegroundColor Green
    $SERVER_FILE = "enhanced_unified_server.py"
} elseif (Test-Path "unified_server.py") {
    Write-Host "  ✅ Basic Unified Server available" -ForegroundColor Green
    $SERVER_FILE = "unified_server.py"
} else {
    Write-Host "  ❌ No unified server found - fallback to separate services" -ForegroundColor Red
    $SERVER_FILE = "api_server.py"
}

# Check if enhanced app exists
if (Test-Path "enhanced_app.py") {
    Write-Host "  ✅ Enhanced Streamlit App available" -ForegroundColor Green
} else {
    Write-Host "  ✅ Basic Streamlit App available" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Starting server..." -ForegroundColor Cyan

# Create user preferences file if it doesn't exist
if (-not (Test-Path "user_preferences.json")) {
    Write-Host "📝 Creating initial preferences file..." -ForegroundColor Yellow
    $initialData = @{
        "_metadata" = @{
            "version" = "2.0"
            "created" = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
        "users" = @{}
    }
    $initialData | ConvertTo-Json -Depth 10 | Out-File -FilePath "user_preferences.json" -Encoding UTF8
}

# Set environment variables for the application
$env:WINDOWS_DEPLOYMENT = "true"
$env:DATA_PERSISTENCE = "true"

# Start the appropriate server
Write-Host "📡 Starting $SERVER_FILE..." -ForegroundColor Cyan

if ($SERVER_FILE -eq "enhanced_unified_server.py") {
    # Enhanced unified server with robust features
    Write-Host "🚀 Using Enhanced Unified Server with robust features" -ForegroundColor Green
    python enhanced_unified_server.py
} elseif ($SERVER_FILE -eq "unified_server.py") {
    # Basic unified server
    Write-Host "🚀 Using Basic Unified Server" -ForegroundColor Green
    python unified_server.py
} else {
    # Fallback: use run_local.py for separate services
    Write-Host "🔄 Fallback: Using run_local.py for separate services..." -ForegroundColor Yellow
    python run_local.py
}

Write-Host ""
Write-Host "✅ Server startup complete!" -ForegroundColor Green
Write-Host "📱 Access the application at the URLs shown above" -ForegroundColor Cyan
