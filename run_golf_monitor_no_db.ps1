# Golf Availability Monitor - No Database Mode
Write-Host "🏌️ Golf Availability Monitor - No Database Mode" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will run the golf monitor without attempting to connect to PostgreSQL." -ForegroundColor Yellow
Write-Host "Results will be saved to JSON files instead." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "Setting DATABASE_ENABLED=false..." -ForegroundColor Blue
$env:DATABASE_ENABLED = "false"

Write-Host ""
Write-Host "Starting golf monitor..." -ForegroundColor Green
python golf_availability_monitor.py --local --immediate

Write-Host ""
Write-Host "Monitor finished. Press any key to exit..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
