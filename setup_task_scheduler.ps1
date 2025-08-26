# Golf Availability Monitor - Task Scheduler Setup Script
# Run this PowerShell script as Administrator to set up the scheduled task

param(
    [string]$TaskName = "Golf Availability Monitor",
    [string]$Description = "Monitors golf course availability and sends email notifications",
    [string]$StartTime = "07:00",
    [string]$RepeatMinutes = 30  # How often to repeat (in minutes)
)

# Get the current script directory
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile = Join-Path $ScriptPath "run_golf_monitor.bat"

Write-Host "Golf Availability Monitor - Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Check if running as administrator
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Error: This script must be run as Administrator." -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if batch file exists
if (-not (Test-Path $BatchFile)) {
    Write-Host "Error: Batch file not found at $BatchFile" -ForegroundColor Red
    Write-Host "Please ensure run_golf_monitor.bat exists in the same directory." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Script location: $ScriptPath" -ForegroundColor Green
Write-Host "Batch file: $BatchFile" -ForegroundColor Green
Write-Host "Task name: $TaskName" -ForegroundColor Green
Write-Host "Start time: $StartTime daily" -ForegroundColor Green
Write-Host "Repeat every: $RepeatMinutes minutes" -ForegroundColor Green
Write-Host ""

# Remove existing task if it exists
try {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
} catch {
    # Task doesn't exist, continue
}

# Create the scheduled task
try {
    Write-Host "Creating scheduled task..." -ForegroundColor Yellow
    
    # Create action - pass "scheduled" parameter to prevent pause on error
    $action = New-ScheduledTaskAction -Execute $BatchFile -Argument "scheduled" -WorkingDirectory $ScriptPath
    
    # Create trigger (daily at specified time, repeating every X minutes)
    $trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
    $trigger.Repetition = New-ScheduledTaskRepetition -Interval (New-TimeSpan -Minutes $RepeatMinutes) -Duration ([TimeSpan]::FromDays(1))
    
    # Create settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 23)
    
    # Create principal (run with highest privileges)
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
    
    # Register the task
    Register-ScheduledTask -TaskName $TaskName -Description $Description -Action $action -Trigger $trigger -Settings $settings -Principal $principal
    
    Write-Host ""
    Write-Host "✅ Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "- Name: $TaskName" -ForegroundColor White
    Write-Host "- Runs daily starting at: $StartTime" -ForegroundColor White
    Write-Host "- Repeats every: $RepeatMinutes minutes" -ForegroundColor White
    Write-Host "- Script: $BatchFile" -ForegroundColor White
    Write-Host "- User: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor White
    Write-Host ""
    Write-Host "Management Commands:" -ForegroundColor Yellow
    Write-Host "- View task: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "- Start now: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "- Stop task: Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "- Remove task: Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "GUI Management:" -ForegroundColor Yellow
    Write-Host "- Open Task Scheduler: taskschd.msc" -ForegroundColor White
    Write-Host "- Look for '$TaskName' in Task Scheduler Library" -ForegroundColor White
    
    # Ask if user wants to test the task now
    Write-Host ""
    $response = Read-Host "Would you like to test the task now? (y/n)"
    if ($response -match "^[Yy]") {
        Write-Host "Starting task..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Task started! Check the output in a few seconds." -ForegroundColor Green
        Write-Host "Note: The first run will open a browser for manual login to golfbox.golf" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error creating scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure you're running as Administrator and try again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "🏌️ Setup complete! The golf monitor will now run automatically." -ForegroundColor Green
Write-Host "The task will start daily at $StartTime and repeat every $RepeatMinutes minutes." -ForegroundColor Green
Read-Host "Press Enter to exit"
